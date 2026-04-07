import asyncio
from bleak import BleakScanner, BleakClient
#from app.config import FAST_POLL_INTERVAL, SLOW_POLL_INTERVAL
#from app.supabase_client import log_telemetry
FAST_INTERVAL = 0.1
SLOW_INTERVAL = 2.0


# FD10 GATT profile (confirmed via BLE Hero)
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY  = "0000fff1-0000-1000-8000-00805f9b34fb"  # responses IN
CHAR_WRITE   = "0000fff2-0000-1000-8000-00805f9b34fb"  # commands OUT

# --- PID Command Dictionaries ---
# PIDs are OBD-II standard commands defined in SAE J1979.
# Format: b"SSPP\r" where SS = service (01 = current data)
# and PP = parameter ID (hex). The \r is the ELM327 command terminator.
# The b prefix means bytes literal — BLE expects raw bytes, not strings.

# Fast loop — queried every FAST_POLL_INTERVAL (default 100ms)
# These need high refresh rates to feel alive on the gauges.
FAST_PIDS = {
    "RPM":      b"010C\r",  # Engine RPM
    "SPEED":    b"010D\r",  # Vehicle speed (km/h, converted to mph in decode)
    "THROTTLE": b"0111\r",  # Throttle position (0-100%)
    "MISFIRE":  b"0101\r",  # Misfire counter + DTC status — key for stutter diagnosis
}

# Slow loop — queried every SLOW_POLL_INTERVAL (default 2000ms)
# These change slowly enough that 2 second updates are sufficient.
# Keeping them slow frees up BLE bandwidth for the fast PIDs.
SLOW_PIDS = {
    "COOLANT_T":  b"0105\r",  # Engine coolant temp (°C converted to °F in decode)
    "SHORT_FT": b"0106\r",  # Short term fuel trim — indicates real time fuel adjustments
    "LONG_FT":  b"0107\r",  # Long term fuel trim — indicates learned fuel adjustments
    "INTAKE_T": b"010F\r",  # Intake air temperature (°C converted to °F in decode)
}


# Decode raw ELM327 response bytes into a value
def decode(pid: str, raw: str) -> tuple[float, str]:
    """
    Decode a raw ELM327 response string into a human-readable value and unit.
    
    The ELM327 returns ASCII hex bytes separated by spaces, e.g. "41 0C 1A F8".
    Each PID has a specific formula defined in SAE J1979 to convert those bytes
    into a meaningful value (RPM, mph, °F, etc.)
    
    Args:
        pid: The PID label string e.g. "RPM", "SPEED", "COOLANT_T"
        raw: The raw response string from the ELM327 e.g. "41 0C 1A F8"
    
    Returns:
        A tuple of (value, unit) e.g. (1726.0, "rpm")
        Returns (None, "") if the response can't be decoded.
    """
    try:
        # Split the raw response into individual parts
        # e.g. "41 0C 1A F8\r\r>" becomes ["41", "0C", "1A", "F8", ">"]
        parts = raw.strip().split()

        # Filter out non-hex characters like ">" prompt, "OK", "SEARCHING...", "NO DATA"
        # We only want valid hex bytes — the actual data from the ECU
        hex_parts = [p for p in parts if all(c in "0123456789ABCDEFabcdef" for c in p)]

        # Need at least 3 parts: service byte (41), PID echo (0C), and one data byte
        # If we have less than 3 something went wrong — return empty
        if len(hex_parts) < 3:
            return None, ""

        # Convert hex strings to integers
        # hex_parts[0] = service response byte (always 41 for service 01, we skip it)
        # hex_parts[1] = PID echo (we already know what we asked for, we skip it)
        # hex_parts[2] = first data byte — called "A" in SAE J1979 formulas
        # hex_parts[3] = second data byte — called "B" in SAE J1979 formulas (if present)
        a = int(hex_parts[2], 16)  # First data byte
        b = int(hex_parts[3], 16) if len(hex_parts) > 3 else 0  # Second data byte or 0

        # Apply the SAE J1979 formula for each PID
        # All formulas are standardized — same for every OBD-II car ever made

        if pid == "RPM":
            # Formula: ((A * 256) + B) / 4
            # ECU stores RPM as a 16-bit integer scaled by 4 for quarter-RPM precision
            # A is the high byte, B is the low byte — combined into one 16-bit number
            return ((a * 256) + b) / 4, "rpm"

        elif pid == "SPEED":
            # Formula: A * 0.621371
            # ECU returns km/h — multiply by 0.621371 to convert to mph
            return a * 0.621371, "mph"

        elif pid == "THROTTLE":
            # Formula: (A * 100) / 255
            # ECU returns 0-255 representing 0-100% throttle position
            return (a * 100) / 255, "%"

        elif pid == "COOLANT_T":
            # Formula: (A - 40) * 9/5 + 32
            # ECU adds 40 to avoid negative bytes (offset encoding)
            # Subtract 40 to get Celsius, then convert to Fahrenheit
            return (a - 40) * 9/5 + 32, "°F"

        elif pid == "SHORT_FT":
            # Formula: ((A - 128) * 100) / 128
            # Fuel trim is centered at 128 = 0%
            # Positive = engine running lean (adding fuel)
            # Negative = engine running rich (reducing fuel)
            # Key diagnostic value for the Jeep stutter investigation
            return ((a - 128) * 100) / 128, "%"

        elif pid == "LONG_FT":
            # Same formula as SHORT_FT
            # SHORT_FT = real time adjustments
            # LONG_FT = learned adjustments stored in ECU memory
            return ((a - 128) * 100) / 128, "%"

        elif pid == "INTAKE_T":
            # Same formula as COOLANT_T — offset encoded Celsius converted to Fahrenheit
            return (a - 40) * 9/5 + 32, "°F"

        else:
            # Unknown PID — return raw A byte as float
            # Safety fallback so we never crash on an unexpected PID
            return float(a), "raw"

    except Exception:
        # If anything goes wrong during decoding return empty
        # This prevents a bad response from crashing the entire polling loop
        return None, ""
class OBDClient:
    def __init__(self, data_queue: asyncio.Queue):
        self.queue = data_queue
        self.client = None
        self.address = None
        self._response_buffer = []
        self._response_event = asyncio.Event()
        self.running = False

    def _handle_notify(self, sender, data):
        text = data.decode("utf-8", errors="replace").strip()
        if text and text != ">":
            self._response_buffer.append(text)
        if ">" in text:
            self._response_event.set()

    async def _send_cmd(self, cmd: bytes, timeout=2.0) -> list:
        self._response_buffer = []
        self._response_event.clear()
        await self.client.write_gatt_char(CHAR_WRITE, cmd)
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return list(self._response_buffer)

    async def _poll_pid(self, label: str, cmd: bytes):
        lines = await self._send_cmd(cmd)
        raw = " ".join(lines)
        value, unit = decode(label, raw)
        if value is not None:
            await self.queue.put({
                "label": label,
                "value": round(value, 2),
                "unit": unit,
            })

    async def _fast_loop(self):
        while self.running:
            for label, cmd in FAST_PIDS.items():
                await self._poll_pid(label, cmd)
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
            await self.client.start_notify(CHAR_NOTIFY, self._handle_notify)
            await self._send_cmd(b"ATZ\r")
            await asyncio.sleep(1)
            await self._send_cmd(b"ATE0\r")
            await self._send_cmd(b"ATL0\r")
            await self._send_cmd(b"ATSP0\r")
            self.running = True
            print("Polling started.")
            await asyncio.gather(
                self._fast_loop(),
                self._slow_loop(),
            )
            await self.client.stop_notify(CHAR_NOTIFY)
