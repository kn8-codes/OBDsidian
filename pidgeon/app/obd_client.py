import asyncio
from bleak import BleakScanner, BleakClient
from app.config import FAST_POLL_INTERVAL, SLOW_POLL_INTERVAL
from app.supabase_client import log_telemetry_batch

TELEMETRY_BATCH_SIZE = 8

# FD10 GATT profile (confirmed via BLE Hero)
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY  = "0000fff1-0000-1000-8000-00805f9b34fb"  # responses IN
CHAR_WRITE   = "0000fff2-0000-1000-8000-00805f9b34fb"  # commands OUT

# ELM327 PID commands
FAST_PIDS = {
    "RPM":      b"010C\r",
    "SPEED":    b"010D\r",
    "THROTTLE": b"0111\r",
    "MISFIRE":  b"0101\r",
}

SLOW_PIDS = {
    "COOLANT":  b"0105\r",
    "SHORT_FT": b"0106\r",
    "LONG_FT":  b"0107\r",
    "INTAKE_T": b"010F\r",
}


def decode(pid: str, raw: str) -> tuple[float | None, str]:
    """Decode a raw ELM327 response string into (value, unit).

    ELM327 responses with echo on look like:
        "010C\r41 0C 0F A0\r\r>"
    With echo off (ATE0):
        "41 0C 0F A0\r\r>"

    We filter to hex-only tokens and treat index 2 as byte A, index 3 as byte B.
    Returns (None, "") for any response that can't be decoded.
    """
    try:
        parts = raw.strip().split()
        hex_parts = [p for p in parts if p and all(c in "0123456789ABCDEFabcdef" for c in p)]
        if len(hex_parts) < 3:
            return None, ""
        a = int(hex_parts[2], 16)
        b = int(hex_parts[3], 16) if len(hex_parts) > 3 else 0

        if pid == "RPM":
            # Formula: ((A*256) + B) / 4  →  rpm
            return ((a * 256) + b) / 4, "rpm"

        elif pid == "SPEED":
            # A = speed in km/h; convert to mph
            return a * 0.621371, "mph"

        elif pid == "THROTTLE":
            # A = throttle position 0–255 → 0–100%
            return (a * 100) / 255, "%"

        elif pid == "COOLANT":
            # A = coolant temp in °C + 40 offset; convert to °F
            return (a - 40) * 9 / 5 + 32, "F"

        elif pid == "SHORT_FT":
            # Short-term fuel trim: (A - 128) * 100 / 128  → percent
            return (a - 128) * 100 / 128, "%"

        elif pid == "LONG_FT":
            # Long-term fuel trim: same formula
            return (a - 128) * 100 / 128, "%"

        elif pid == "INTAKE_T":
            # Intake air temp: A - 40 in °C; convert to °F
            return (a - 40) * 9 / 5 + 32, "F"

        elif pid == "MISFIRE":
            # PID 01 01: byte A bit 7 = MIL, bits 0-6 = confirmed DTC count
            return float(a & 0x7F), "dtcs"

        return None, ""

    except (ValueError, IndexError):
        return None, ""


class OBDClient:
    """BLE OBD-II client for the FNIRSI FD10 adapter.

    Usage (matches main.py lifespan pattern):
        obd = OBDClient()
        connected = await obd.connect()
        if connected:
            asyncio.create_task(obd.start_polling(session_id))
        ...
        await obd.disconnect()
    """

    def __init__(self):
        self.connected: bool = False
        self.device_name: str | None = None
        self.live_data: dict = {}
        self._client: BleakClient | None = None
        self._response_buf: str = ""
        self._response_event: asyncio.Event = asyncio.Event()
        self._telemetry_buffer: list[dict] = []

    # ------------------------------------------------------------------
    # BLE notification handler
    # ------------------------------------------------------------------

    def _handle_notify(self, sender, data: bytearray):
        """Accumulate notification chunks; set event when ELM327 prompt arrives."""
        chunk = data.decode("utf-8", errors="replace")
        self._response_buf += chunk
        if ">" in chunk:
            self._response_event.set()

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    async def _find_device(self) -> str | None:
        print("Scanning for FNIRSI FD10...")
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if d.name and "OBD" in d.name.upper():
                print(f"Found: {d.name} | {d.address}")
                self.device_name = d.name
                return d.address
        print("FD10 not found — is it plugged in and powered?")
        return None

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Scan, connect, and run ELM327 init sequence. Returns True on success."""
        address = await self._find_device()
        if not address:
            return False

        try:
            self._client = BleakClient(address)
            await self._client.connect()
            await self._client.start_notify(CHAR_NOTIFY, self._handle_notify)
            print("BLE connected, initialising ELM327...")

            # Full reset — allow extra time for chip to boot
            await self._command("ATZ\r")
            await asyncio.sleep(1.5)

            # Echo off so responses don't repeat the command back
            await self._command("ATE0\r")
            # Disable linefeed characters (cleaner parsing)
            await self._command("ATL0\r")
            # Auto-detect OBD protocol
            await self._command("ATSP0\r")

            self.connected = True
            print("ELM327 ready.")
            return True

        except Exception as e:
            print(f"BLE connect failed: {e}")
            await self._cleanup()
            return False

    async def disconnect(self):
        """Stop polling, flush any buffered telemetry, and close BLE connection."""
        self.connected = False
        await self._flush_telemetry()
        await self._cleanup()

    async def _cleanup(self):
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(CHAR_NOTIFY)
                await self._client.disconnect()
            except Exception as e:
                print(f"BLE disconnect error: {e}")
        self._client = None

    # ------------------------------------------------------------------
    # Low-level command/query helpers
    # ------------------------------------------------------------------

    async def _command(self, command: str, timeout: float = 3.0) -> str:
        """Send an AT command string, wait for '>' prompt, return response."""
        if not self._client or not self._client.is_connected:
            return ""
        self._response_buf = ""
        self._response_event.clear()
        await self._client.write_gatt_char(CHAR_WRITE, command.encode())
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self._response_buf

    async def _query(self, command: bytes, timeout: float = 3.0) -> str:
        """Send a PID command (bytes), wait for '>' prompt, return raw response."""
        if not self._client or not self._client.is_connected:
            return ""
        self._response_buf = ""
        self._response_event.clear()
        await self._client.write_gatt_char(CHAR_WRITE, command)
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self._response_buf

    # ------------------------------------------------------------------
    # Telemetry buffer helpers
    # ------------------------------------------------------------------

    def _buffer_reading(self, session_id: str, pid: str, value: float, unit: str):
        """Append one reading to the in-memory buffer."""
        self._telemetry_buffer.append({
            "session_id": session_id,
            "pid": pid,
            "value": value,
            "unit": unit,
        })

    async def _flush_telemetry(self):
        """Batch-insert all buffered rows, then clear the buffer."""
        if not self._telemetry_buffer:
            return
        batch = self._telemetry_buffer[:]
        self._telemetry_buffer.clear()
        try:
            await log_telemetry_batch(batch)
        except Exception as e:
            print(f"Telemetry flush error: {e}")

    # ------------------------------------------------------------------
    # Polling loops
    # ------------------------------------------------------------------

    async def start_polling(self, session_id: str):
        """Launch fast and slow polling loops concurrently. Runs until disconnected."""
        await asyncio.gather(
            self._fast_loop(session_id),
            self._slow_loop(session_id),
        )

    async def _fast_loop(self, session_id: str):
        """Poll FAST_PIDS (RPM, speed, throttle, misfire) on FAST_POLL_INTERVAL."""
        while self.connected:
            for pid, cmd in FAST_PIDS.items():
                if not self.connected:
                    break
                try:
                    raw = await self._query(cmd)
                    value, unit = decode(pid, raw)
                    if value is not None:
                        self.live_data[pid] = {"value": value, "unit": unit}
                        self._buffer_reading(session_id, pid, value, unit)
                        if len(self._telemetry_buffer) >= TELEMETRY_BATCH_SIZE:
                            await self._flush_telemetry()
                except Exception as e:
                    print(f"Fast poll error [{pid}]: {e}")
            await asyncio.sleep(FAST_POLL_INTERVAL)

    async def _slow_loop(self, session_id: str):
        """Poll SLOW_PIDS (coolant, fuel trim, intake temp) on SLOW_POLL_INTERVAL."""
        while self.connected:
            for pid, cmd in SLOW_PIDS.items():
                if not self.connected:
                    break
                try:
                    raw = await self._query(cmd)
                    value, unit = decode(pid, raw)
                    if value is not None:
                        self.live_data[pid] = {"value": value, "unit": unit}
                        self._buffer_reading(session_id, pid, value, unit)
                except Exception as e:
                    print(f"Slow poll error [{pid}]: {e}")
            # flush after each slow cycle so these don't wait too long
            await self._flush_telemetry()
            await asyncio.sleep(SLOW_POLL_INTERVAL)
