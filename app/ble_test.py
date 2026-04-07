import asyncio
from bleak import BleakScanner, BleakClient

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY = "0000fff1-0000-1000-8000-00805f9b34fb"
CHAR_WRITE  = "0000fff2-0000-1000-8000-00805f9b34fb"

def handle_notification(sender, data):
    print(f"<-- {data.decode('utf-8', errors='replace').strip()}")

async def find_fd10():
    print("Scanning for OBDII...")
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        if d.name and "OBD" in d.name.upper():
            print(f"Found: {d.name} | {d.address}")
            return d.address
    print("FD10 not found. Is it plugged in?")
    return None

async def connect_and_test(address):
    print(f"Connecting to {address}...")
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        await client.start_notify(CHAR_NOTIFY, handle_notification)
        print("Subscribed to FFF1")
        print("--> ATZ")
        await client.write_gatt_char(CHAR_WRITE, b"ATZ\r")
        await asyncio.sleep(1)
        print("--> ATSP0")
        await client.write_gatt_char(CHAR_WRITE, b"ATSP0\r")
        await asyncio.sleep(1)
        print("--> 010C RPM")
        await client.write_gatt_char(CHAR_WRITE, b"010C\r")
        await asyncio.sleep(2)
        await client.stop_notify(CHAR_NOTIFY)

async def main():
    address = await find_fd10()
    if address:
        await connect_and_test(address)

asyncio.run(main())
