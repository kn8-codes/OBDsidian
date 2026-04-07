import asyncio
from bleak import BleakScanner, BleakClient
from app.config import FAST_POLL_INTERVAL, SLOW_POLL_INTERVAL
from app.supabase_client import log_telemetry

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
    "COOLANT":   b"0105\r",
    "SHORT_FT":  b"0106\r",
    "LONG_FT":   b"0107\r",
    "INTAKE_T":  b"010F\r",
}

# Decode raw ELM327 response bytes into a value
def decode(pid: str, raw: str) -> tuple[float, str]:
    try:
        parts = raw.strip().split()
        # Filter out non-hex parts
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
        elif pid == "COOLANT":
            return (a - 40) * 9/5 + 32, "°F​​​​​​​​​​​​​​​​
