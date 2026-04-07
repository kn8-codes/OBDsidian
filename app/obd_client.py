import asyncio
from bleak import BleakScanner, BleakClient
from app.config import FAST_POLL_INTERVAL, SLOW_POLL_INTERVAL
from app.supabase_client import log_telemetry

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
        elif pid == "COOLANT_T":
            return (a - 40) * 9/5 + 32, "°F"
