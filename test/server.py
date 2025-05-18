import asyncio
import websockets
import random

PORT = 3000

async def handler(websocket):  # Only one parameter now
    print(f"Client connected: {websocket.remote_address}")
    try:
        while True:
            data = bytes(random.getrandbits(8) for _ in range(1024))
            await websocket.send(data)
            await asyncio.sleep(1)
    except websockets.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"WebSocket server started on port {PORT}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
