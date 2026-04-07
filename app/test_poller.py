# app/test_poller.py

import asyncio
import queue
from obd_client import OBDClient

async def main():
     queue = asyncio.Queue()
     client = OBDClient(data_queue=queue)

```
async def print_queue():
    while True:
        reading = await queue.get()
        print(f"  {reading['label']:10} {reading['value']}")

await asyncio.gather(
    client.run(),
    print_queue(),
)
```

asyncio.run(main())