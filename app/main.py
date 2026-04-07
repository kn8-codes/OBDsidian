import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.obd_client import OBDClient
from app.supabase_client import create_session, end_session

obd = OBDClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    connected = await obd.connect()
    if connected:
        session_id = await create_session()
        asyncio.create_task(obd.start_polling(session_id))
        app.state.session_id = session_id
    else:
        app.state.session_id = None
    yield
    # Shutdown
    if app.state.session_id:
        await end_session(app.state.session_id)
    await obd.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "connected": obd.connected,
        "session_id": app.state.session_id
    }

@app.get("/data")
async def data():
    return obd.live_data

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if obd.live_data:
                await websocket.send_text(json.dumps(obd.live_data))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
