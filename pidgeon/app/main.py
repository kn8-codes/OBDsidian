import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.obd_client import OBDClient

# Shared state — module-level so lifespan and endpoints share references
data_queue: asyncio.Queue = asyncio.Queue()
live_data: dict = {}          # {PID: {"value": ..., "unit": ...}}
client_queues: set = set()    # one asyncio.Queue per connected WebSocket


async def _broadcast_loop():
    """Drain the OBD data queue, update live_data, fan out to all WebSocket clients."""
    while True:
        frame = await data_queue.get()
        pid = frame["label"]
        live_data[pid] = {"value": frame["value"], "unit": frame["unit"]}

        msg = json.dumps({"pid": pid, "value": frame["value"], "unit": frame["unit"]})
        dead: set = set()
        for q in client_queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.add(q)
        client_queues.difference_update(dead)


@asynccontextmanager
async def lifespan(app: FastAPI):
    obd = OBDClient(data_queue)
    app.state.obd = obd

    obd_task = asyncio.create_task(obd.run())
    bcast_task = asyncio.create_task(_broadcast_loop())

    yield

    # Signal the polling loops to stop, then cancel both tasks
    obd.running = False
    for task in (obd_task, bcast_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    obd: OBDClient = app.state.obd
    return {
        "status": "ok",
        "polling": obd.running,
        "pids_seen": list(live_data.keys()),
    }


@app.get("/data")
async def data():
    return live_data


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    client_queues.add(q)

    # Send current snapshot so the client has something to render immediately
    if live_data:
        await websocket.send_text(json.dumps({"snapshot": live_data}))

    try:
        while True:
            msg = await q.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
    finally:
        client_queues.discard(q)
