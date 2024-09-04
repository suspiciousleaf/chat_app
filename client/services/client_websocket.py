import asyncio
import websockets
from websockets import WebSocketClientProtocol
import time
import json
from os import getenv
from dotenv import load_dotenv

import logging
logger = logging.getLogger('websockets')
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())

load_dotenv()

# WS_URL = "ws://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
WEBSOCKET_ENDPOINT = "/ws"


class MyWebSocket:
    def __init__(self, auth_token: dict, username: str | None = None):
        self.websocket_url: str = f"{WS_URL}{WEBSOCKET_ENDPOINT}"
        self.websocket: WebSocketClientProtocol | None = None
        self.auth_token: dict = auth_token
        self.username = username

    async def connect(self):
        try:
            extra_headers = {
                "Authorization": f"Bearer {self.auth_token.get('access_token', '')}"
            }
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=10,
                extra_headers=extra_headers,
            )
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"Invalid status code: {e.status_code}")
        except TimeoutError as e:
            logger.warning(f"{self.username + ': ' if self.username else ''}A timeout error occurred: {str(e)}")
        except Exception as e:
            logger.warning(e, exc_info=True)
            print(
                f"{self.username + ': ' if self.username else ''}An error occurred: {str(e)}"
            )

        if not self.websocket:
            print(
                f"{self.username + ': ' if self.username else ''}Connection failed. Reconnecting in 5 seconds..."
            )
            await asyncio.sleep(5)
            await self.connect()

    async def send_message(self, message: dict):
        await self.websocket.send(json.dumps(message))

    async def close(self):
        """Close the websocket connection if it's open"""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"An error occurred while closing the WebSocket: {e}")
            finally:
                self.websocket = None
