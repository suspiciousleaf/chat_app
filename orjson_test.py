import orjson
import json
import time
import websockets
import asyncio
import message_pb2
from google.protobuf.internal import api_implementation
print(f"This should be 'upb': {api_implementation.Type()=}\n")


message = message_pb2.ChatMessage()
parsed_message = message_pb2.ChatMessage()

message.sender = "David"
message.active_connections = 35
message.memory_usage = 0.554781258874
message.data.extend(["Gatito", "Ravioli"])

x = {
  "name": "David",
  "age": 35,
  "random_float": 0.554781258874,
  "cats": ["Gatito", "Ravioli"]
}

NUM_TESTS = 1000000
RUN_PERF_TESTS = True
RUN_WS_TEST = False
TARGET = "wss://echo.websocket.events/"

def perf_tests():
    # Protobuf
    t0 = time.perf_counter()
    for _ in range(NUM_TESTS):
        binary_data = message.SerializeToString()
    t1 = time.perf_counter()
    proto_serialize_time = (t1 - t0)*1000
    print(f"Protobuf serialize:   {proto_serialize_time:,.0f} ms")

    for _ in range(NUM_TESTS):
        parsed_message.ParseFromString(binary_data)
    t2 = time.perf_counter()
    proto_deserialize_time = (t2 - t1)*1000
    print(f"Protobuf deserialize: {proto_deserialize_time:,.0f} ms")
    print(f"Protobuf total:       {proto_serialize_time + proto_deserialize_time:,.0f} ms\n")

    # Orjson
    t0 = time.perf_counter()
    for _ in range(NUM_TESTS):
        x_dump = orjson.dumps(x)
    t1 = time.perf_counter()
    orjson_serialize_time = (t1 - t0)*1000
    print(f"Orjson serialize:   {orjson_serialize_time:,.0f} ms")

    for _ in range(NUM_TESTS):
        x_1 = orjson.loads(x_dump)
    t2 = time.perf_counter()
    orjson_deserialize_time = (t2 - t1)*1000
    print(f"Orjson deserialize: {orjson_deserialize_time:,.0f} ms")
    print(f"Orjson total:       {orjson_serialize_time + orjson_deserialize_time:,.0f} ms\n")

    # Json
    t0 = time.perf_counter()
    for _ in range(NUM_TESTS):
        x_dump = json.dumps(x)
    t1 = time.perf_counter()
    json_serialize_time = (t1 - t0)*1000
    print(f"Json serialize:   {json_serialize_time:,.0f} ms")

    for _ in range(NUM_TESTS):
        x_1 = json.loads(x_dump)
    t2 = time.perf_counter()
    json_deserialize_time = (t2 - t1)*1000
    print(f"Json deserialize: {json_deserialize_time:,.0f} ms")
    print(f"Json total:       {json_serialize_time + json_deserialize_time:,.0f} ms\n")

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