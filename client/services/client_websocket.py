import asyncio
import websockets
from websockets import WebSocketClientProtocol, ConnectionClosedOK, ConnectionClosedError
import time
import json
import orjson
from orjson import JSONEncodeError 
from os import getenv
from dotenv import load_dotenv
import traceback
from logging import Logger


load_dotenv()

# WS_URL = "ws://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
WEBSOCKET_ENDPOINT = "/ws"


class MyWebSocket:
    def __init__(self, logger: Logger, auth_token: dict, username: str | None = None):
        self.logger = logger
        self.websocket_url: str = f"{WS_URL}{WEBSOCKET_ENDPOINT}"
        self.websocket: WebSocketClientProtocol | None = None
        self.auth_token: dict = auth_token
        self.username = username
        self.connected = False

    async def connect(self):
        while not self.connected:
            try:
                extra_headers = {
                    "Authorization": f"Bearer {self.auth_token.get('access_token', '')}"
                }
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    # ping_interval=20,
                    ping_timeout=None,
                    open_timeout=None,
                    extra_headers=extra_headers,
                )
                self.connected = True
            except websockets.exceptions.InvalidStatusCode as e:
                self.logger.debug(f"Invalid status code: {e.status_code}")
            except ConnectionClosedError as e:
                self.logger.info(f"Connection was closed unexpectedly: {e}")
            except ConnectionResetError as e:
                self.logger.info(f"Connection reset by remote host: {e}")
            except TimeoutError as e:
                pass
            except Exception as e:
                self.logger.info(
                    f"{self.username + ': ' if self.username else ''}An error occurred: {type(e).__name__}: {e}"
                )

            if not self.connected:
                self.logger.debug(
                    f"{self.username + ': ' if self.username else ''}Connection failed. Reconnecting in 5 seconds..."
                )
                await asyncio.sleep(5)



    async def send_message(self, message: dict):
        """Send message via WebSocket. Provide dict and it will be converted to protobuf message and serialized"""
        if not self.connected:
            # self.logger.info("Cannot send message, WebSocket is not connected.")
            raise ConnectionError
        try:
            # await self.websocket.send(json.dumps(message))
            await self.websocket.send(orjson.dumps(message))
        except JSONEncodeError as e:
            self.logger.warning(f"JSONEncodeError: {e}: {message=}")
        except websockets.exceptions.ConnectionClosedOK:
            self.connected = False
            raise websockets.exceptions.ConnectionClosedOK
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.debug(f"Connection closed unexpectedly: {e}. Reconnecting...")
            self.connected = False
            await self.connect() 
            await self.send_message(message) 
        except Exception as e:
            self.logger.warning(f"An error occurred while sending message: {type(e).__name__}: {e}")

    async def receive_message(self):
        """Receive messages from the WebSocket"""
        if not self.connected:
            # self.logger.info("Cannot receive message, WebSocket is not connected.")
            return 
        try:
            message = await self.websocket.recv()
            # self.logger.info(f"{message=}, {type(message)=}")
            return message
            # return await self.websocket.recv()
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.debug(f"Connection closed unexpectedly: {e}. Reconnecting...")
            self.connected = False
            await self.connect()  
        except ConnectionClosedOK as e:
            raise ConnectionClosedOK(*e.args)
        except Exception as e: 
            self.logger.info(f"An error occurred while receiving message: {type(e).__name__}: {e}")

    async def close(self):
        """Close the WebSocket connection if it's open."""
        if self.websocket and self.connected:
            try:
                await self.websocket.close()
                # await asyncio.sleep(1)
                self.logger.debug(f"{self.username}: WebSocket connection closed.")
            except ConnectionClosedError as e:
                self.logger.debug(f"Connection closed unexpectedly during closure: ConnectionClosedError: {e}")
            except Exception as e:
                self.logger.info(f"An error occurred while closing the WebSocket: {type(e).__name__}: {e}")
            finally:
                self.websocket = None
                self.connected = False
