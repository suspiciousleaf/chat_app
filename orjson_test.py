import orjson
import json
import time
import websockets
import asyncio

x = {
  "name": "David",
  "age": 35,
  "random_float": 0.554781258874,
  "cats": ["Gatito", "Ravioli"]
}

RUN_PERF_TESTS = False
RUN_WS_TEST = True
TARGET = "wss://echo.websocket.events/"

def perf_tests():
    t0 = time.perf_counter()
    for _ in range(1000000):
        x_dump = orjson.dumps(x)
    t1 = time.perf_counter()
    print(f"Orjson serialize: {(t1 - t0)*1000:.0f} ms")

    for _ in range(1000000):
        x_1 = orjson.loads(x_dump)
    t2 = time.perf_counter()
    print(f"Orjson deserialize: {(t2 - t1)*1000:.0f} ms")

    t0 = time.perf_counter()
    for _ in range(1000000):
        x_dump = json.dumps(x)
    t1 = time.perf_counter()
    print(f"Json serialize: {(t1 - t0)*1000:,.0f} ms")

    for _ in range(1000000):
        x_1 = json.loads(x_dump)
    t2 = time.perf_counter()
    print(f"Json deserialize: {(t2 - t1)*1000:,.0f} ms")

async def ws_test(message: bytes):
    async with websockets.connect(TARGET) as ws:
        # Send the message every 5 seconds in a loop
        async def send_message():
            while True:
                await ws.send(message)
                print(f"Sent message: {message}")
                await asyncio.sleep(5)

        # Listen for messages from the WebSocket
        async def receive_message():
            while True:
                received = await ws.recv()
                print(f"Received message raw: {received}")
                try:
                    print(f"Received message: {orjson.loads(received)}")
                except:
                    pass
        
        # Run sending and receiving concurrently
        await asyncio.gather(send_message(), receive_message())


if __name__ == "__main__":
    if RUN_PERF_TESTS:
        perf_tests()
    if RUN_WS_TEST:
        x_dump = orjson.dumps(x)
        asyncio.run(ws_test(x_dump))