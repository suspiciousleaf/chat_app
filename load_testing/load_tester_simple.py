import asyncio
import websockets
import time
from os import getenv

from dotenv import load_dotenv

load_dotenv()

URL = getenv("URL")
# URL = "http://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
# WS_URL = "ws://127.0.0.1:8000"

class WebSocketClient:
    def __init__(self, uri, message, client_number, total_clients, verbose = False, interval=5):
        self.uri = f"{uri}/ws"
        self.message = message
        self.client_number = client_number
        self.total_clients = total_clients
        self.verbose = verbose
        self.interval = interval

    async def connect_and_send(self):
        try:
            async with websockets.connect(self.uri, timeout=30) as websocket: 
                while True:
                    await websocket.send(self.message)
                    if self.verbose:
                        print(f"{self.client_number} Sent: {self.message}")
                    else:
                        if not self.client_number % self.total_clients:
                            print(f"{self.client_number} Sent: {self.message}")
                    
                    response = await websocket.recv()
                    if self.verbose:
                        print(f"{self.client_number} Received: {response}")
                    else:
                        if not self.client_number % self.total_clients:
                            print(f"{self.client_number} Received: {response}")
                    
                    await asyncio.sleep(self.interval)
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
            print(f"Client {self.client_number} experienced a timeout or connection error: {e}")


class LoadTester:
    def __init__(self, uri, message, num_clients=100, verbose = False, interval=5, connection_delay=0):
        self.uri = uri
        self.message = message
        self.num_clients = num_clients
        self.verbose = verbose
        self.interval = interval
        self.clients: list[WebSocketClient] = []
        self.connection_delay = connection_delay

    def create_clients(self):
        for client_number in range(self.num_clients):
            client = WebSocketClient(self.uri, self.message, client_number +1 , self.num_clients, self.verbose, self.interval)
            self.clients.append(client)

    async def start_clients(self):
        tasks = []
        for client in self.clients:
            tasks.append(client.connect_and_send())
            await asyncio.sleep(self.connection_delay)
        await asyncio.gather(*tasks)


    def run(self):
        self.create_clients()
        asyncio.run(self.start_clients())

if __name__ == "__main__":
    try:
        uri = WS_URL
        message = "Hello, FastAPI WebSocket server!"
        # print(uri)
        load_tester = LoadTester(uri, message, num_clients=200, verbose=False, interval=2, connection_delay = 0.05)
        load_tester.run()
    except KeyboardInterrupt:
        print("Load test shutting down")
