import asyncio
from bleak import BleakScanner, BleakClient
from app.supabase_client import SessionLogger

FAST_INTERVAL = 0.25
SLOW_INTERVAL = 2.0

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY  = "0000fff1-0000-1000-8000-00805f9b34fb"
CHAR_WRITE   = "0000fff2-0000-1000-8000-00805f9b34fb"

FAST_PIDS = {
    "RPM":      b"010C\r",
    "SPEED":    b"010D\r",
    "THROTTLE": b"0111\r",
    "MISFIRE":  b"0101\r",
}

SLOW_PIDS = {
    "COOLANT_T": b"0105\r",
    "SHORT_FT":  b"0106\r",
    "LONG_FT":   b"0107\r",
    "INTAKE_T":  b"010F\r",
}

def decode(pid, raw):
    try:
        parts = raw.strip().split()
        hex_parts = [p for p in parts if all(c in "0123456789ABCDEFabcdef" for c in p)]
        if len(hex_parts) < 3:
            return None, ""
        a = int(hex_parts[2], 16)
        b = int(hex_parts[3], 16) if len(hex_parts) > 3 else 0
        if pid == "RPM":
            return ((a * 256) + b) / 4, "rpm"
        elif pid == "SPEED":
            return a * 0.621371, "mph"
        elif pid == "THROTTLE":
            return (a * 100) / 255, "%"
        elif pid == "COOLANT_T":
            return (a - 40) * 9/5 + 32, "degF"
        elif pid == "SHORT_FT":
            return ((a - 128) * 100) / 128, "%"
        elif pid == "LONG_FT":
            return ((a - 128) * 100) / 128, "%"
        elif pid == "INTAKE_T":
            return (a - 40) * 9/5 + 32, "degF"
        else:
            return float(a), "raw"
    except Exception:
        return None, ""

class OBDClient:
    def __init__(self, data_queue):
        self.queue = data_queue
        self.client = None
        self.address = None
        self._response_buffer = []
        self._response_event = asyncio.Event()
        self.running = False
        self.logger = SessionLogger()

    def _handle_notify(self, sender, data):
        text = data.decode("utf-8", errors="replace").strip()
        if text and text != ">":
            self._response_buffer.append(text)
        if ">" in text:
            self._response_event.set()

    async def _send_cmd(self, cmd, timeout=2.0):
        self._response_buffer = []
        self._response_event.clear()
        await self.client.write_gatt_char(CHAR_WRITE, cmd)
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return list(self._response_buffer)

    async def _poll_pid(self, label, cmd):
        lines = await self._send_cmd(cmd)
        raw = " ".join(lines)
        value, unit = decode(label, raw)
        if value is not None:
            await self.queue.put({"label": label, "value": round(value, 2), "unit": unit})
            self.logger.log_telemetry(label, round(value, 2), unit)

    async def _fast_loop(self):
        while self.running:
            for label, cmd in FAST_PIDS.items():
                await self._poll_pid(label, cmd)
		await asyncio.sleep(0.05)
            await asyncio.sleep(FAST_INTERVAL)

    async def _slow_loop(self):
        while self.running:
            for label, cmd in SLOW_PIDS.items():
                await self._poll_pid(label, cmd)
            await asyncio.sleep(SLOW_INTERVAL)

    async def find_device(self):
        print("Scanning for OBDII...")
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if d.name and "OBD" in d.name.upper():
                print(f"Found: {d.name} | {d.address}")
                return d.address
        print("Device not found.")
        return None

    async def run(self):
        self.address = await self.find_device()
        if not self.address:
            return
        async with BleakClient(self.address) as self.client:
            print(f"Connected: {self.client.is_connected}")
            self.logger.start_session()
            await self.client.start_notify(CHAR_NOTIFY, self._handle_notify)
            await self._send_cmd(b"ATZ\r")
            await asyncio.sleep(1)
            await self._send_cmd(b"ATE0\r")
            await self._send_cmd(b"ATL0\r")
            await self._send_cmd(b"ATSP0\r")
            self.running = True
            print("Polling started.")
            try:
                await asyncio.gather(
                    self._fast_loop(),
                    self._slow_loop(),
                )
            finally:
                self.logger.end_session()
                await self.client.stop_notify(CHAR_NOTIFY)
