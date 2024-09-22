import time
import asyncio
import json
import orjson
from pathlib import Path
from os import getenv
import datetime
from sys import getsizeof
from logging import Logger

from fastapi import WebSocket
from fastapi.websockets import WebSocketState, WebSocketDisconnect
from dotenv import load_dotenv
import psutil

# from server.services.db_manager import DatabaseManager
from services.db_manager import DatabaseManager



env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)

REDIS_QUEUE = getenv("REDIS_QUEUE")
MAX_RECONNECT_ATTEMPTS = int(getenv("MAX_RECONNECT_ATTEMPTS"))
RECONNECT_DELAY = getenv("RECONNECT_DELAY")
CACHED_MESSAGE_UPLOAD_TIMER = int(getenv("CACHED_MESSAGE_UPLOAD_TIMER"))


class ConnectionManager:
    def __init__(self, logger:Logger, db: DatabaseManager):
        self.logger: Logger = logger
        self.db: DatabaseManager = db
        self.listener_task = None
        # Dict of active connections, {"username":{"ws": websocket, "channels": {"welcome", "hello", etc}}
        self.active_connections: dict[str, dict[WebSocket, set]] = {}
        # Dict of channels with pointers to the websockets of active subscribers {"channel":{"username": websocket"}}
        self.channel_subscribers: dict[str, dict] = {}
        self.message_cache: list[dict] = []
        self.time_last_message_backup: int = round(time.time())
        self.load_testing: bool = False
        # self.message_volume = 0
        # self.message_volume_timer = None
        self.ema_window = 3
        self.alpha = 2 / (self.ema_window + 1)  # Smoothing factor based on window size
        

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        channels: set = self.db.retrieve_channels(username)
        self.active_connections[username] = {"ws": websocket, "channels": channels}
        for channel in channels:
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = {}
            self.channel_subscribers[channel][username] = websocket
        if username == "monitor":
            self.logger.info("Load testing beginning")
            self.load_testing = True
            # Reset load testing values
            self.message_volume = 0
            self.message_volume_timer = time.perf_counter()
            self.ema_message_volume = 0
            
        else:
            await self.send_channel_subscriptions(websocket, channels)
            # await self.send_channel_history(websocket, channels)

        # Starts the message listener once at least one user is connected.
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.start_listener())
            self.logger.info("First connection opened, starting listener")

        self.logger.info(f"Active connections: {len(self.active_connections)}")

    async def send_channel_subscriptions(self, websocket: WebSocket, channels: set):
        """Send a formatted message to the client with a list of channels that the user account is subscribed to"""

        info_message = {"event": "channel_subscriptions", "data": list(channels)}
        # await websocket.send_text(json.dumps(info_message))
        await websocket.send_bytes(orjson.dumps(info_message))

    async def send_channel_history(self, websocket: WebSocket, channels: set):
        """Send the message history for all subscribed channels to the client"""
        message_history: list = self.db.retrieve_message_history(channels)

        # If any messages are in the cache, add the to the message history to send to newly logged in accounts
        if self.message_cache:
            for message in self.message_cache:
                if message.get("channel") in channels:
                    message_history.extend(message)

        # history_message = {"event": "message history", "data": message_history}

        # await websocket.send_bytes(orjson.dumps(history_message))


        # Message history can exceed the maximum size for a websocket message (1MB), so the section below checks the size and breaks it down into multiple messages if it exceeds this limit. Currently not very performant as it serializes each message twice

        history_message = {"event": "message history", "data": []}
        max_size = 1024 * 900  # 1 MB size limit for websocket message, with an allowance for getsizeof inaccurate estimate

        current_size = 0

        for message in message_history:
            message_size = getsizeof(orjson.dumps(message))

            if current_size + message_size > max_size:
                await websocket.send_bytes(orjson.dumps(history_message))
                # Reset for the next chunk
                history_message["data"] = []
                current_size = 0

            history_message["data"].append(message)
            current_size += message_size

        # Send any remaining messages
        if history_message["data"]:
            await websocket.send_bytes(orjson.dumps(history_message))

    async def leave_channel(self, username: str, channel: str):
        """Remove channel subscription for username"""
        self.db.remove_channel(username, channel)
        # Check channel is present in list of active users and channel subscriptions, and remove it
        if channel in self.active_connections[username]["channels"]:
            self.active_connections[username]["channels"].remove(channel)
        if username in self.channel_subscribers[channel]:
            self.channel_subscribers[channel].pop(username)

    async def add_channel(self, username, channel: str):
        """Add a new channel for username"""
        # Add channel to username's channel list in database
        self.db.add_channel(username, channel)
        # Add channel to active_connections and channel_subscribers
        self.active_connections[username]["channels"].add(channel)
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = {}
        self.channel_subscribers[channel][username] = self.active_connections[username][
            "ws"
        ]
        await self.send_channel_subscriptions(
            self.active_connections[username]["ws"], {channel}
        )
        # await self.send_channel_history(
        #     self.active_connections[username]["ws"], {channel}
        # )

    async def disconnect(self, username: str):
        # TODO Could use this to send a 'user disconnected' message to the channel

        # Loop through all channels that a username is subscribed to, and remove that username from each channel's dict of subscribed users. If that channel no longer has any subscribed users connected, remove it from the dict of active channels. Finally remove user from the dict of active connections
        if username == "monitor":
            self.load_testing = False
            self.logger.info("Stopped load testing")
            self.message_volume = 0
            self.message_volume_timer = None
            self.ema_message_volume = 0
        try:
            if username in self.active_connections:
                websocket: WebSocket =  self.active_connections[username].get("ws")
                for channel in self.active_connections[username].get("channels", []):
                    self.channel_subscribers.get(channel, {}).pop(username, None)
                    if not self.channel_subscribers.get(channel):
                        self.channel_subscribers.pop(channel, None)
                self.active_connections.pop(username, None)
                await websocket.close()
        except RuntimeError:
            pass
        except Exception as e:
            self.logger.warning(f"Exception during disconnect: {type(e).__name__}: {e}")

        # Disable listener if there are no active connections
        if not self.active_connections and self.listener_task:
            self.listener_task.cancel()
            self.listener_task = None
            if self.message_cache:
                self.logger.info(
                    f"Upload cache triggered by disconnect, {len(self.active_connections) = }, {len(self.message_cache) = }, {len(self.active_connections) = }"
                )
                await self.upload_cached_messages()
            self.logger.info("No active connections, stopping listener. Message cache uploaded")

    async def broadcast(self, message: dict):
        """Send message to all active connections that are subscribed to that channel"""
        channel = message.get("channel")
        message_raw = orjson.dumps(message)
        closed_connections = []
        tasks = []

        # Iterate over users and websockets subscribed to the channel
        for user, websocket in self.channel_subscribers.get(channel, {}).items():
            # Append the send_message task to the list of tasks
            tasks.append(self.send_message(user, websocket, message_raw, closed_connections))
        
        # Gather and await the results of the tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle closed connections
        if closed_connections:
            disconnect_tasks = []
            self.logger.debug(f"Closed connections: {closed_connections}")
            for user in closed_connections:
                disconnect_tasks.append(self.disconnect(user))
        
            # Gather and await the results of the tasks
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)


    async def send_message(self, user: str, websocket: WebSocket, message_raw: bytes, closed_connections: list):
        if user not in self.active_connections:
            return
        try:
            await websocket.send_bytes(message_raw)
            if self.load_testing:
                self.message_volume += 1
                if self.message_volume_timer is None:
                    self.message_volume_timer = time.perf_counter()
        except WebSocketDisconnect:
            closed_connections.append(user)
        except Exception as e:
            if str(e) == 'Cannot call "send" once a close message has been sent.':
                closed_connections.append(user)
            else:
                self.logger.warning(f"Exception sending message, closing connection: {user in self.active_connections=} {type(e).__name__}: {e}")
                closed_connections.append(user)

    async def handle_incoming_message(self, message: dict):
        self.logger.debug(f"Received: {message}")
        message_event = message.get("event")
        if message_event == "message":
            # Timestamp is generated by server for UTC and converted to an ISO 8601 format string for redis and database compatibility
            message["sent_at"] = self.db.adapt_datetime_iso(
                datetime.datetime.now(datetime.timezone.utc)
            )
            await self.broadcast(message)
            self.message_cache.append(message)
            # TODO Add graceful error handling for batch inserts / fails
        elif message_event == "leave_channel":
            await self.leave_channel(message.get("username"), message.get("channel"))
        elif message_event == "add_channel":
            await self.add_channel(message.get("username"), message.get("channel"))
        elif message_event == "perf_test":
            await self.handle_perf_ping(message)

    async def start_listener(self):
        """Method to take cached messages and batch upload them to the database if conditions are met"""
        while True:
            num_messages: int = len(self.message_cache)
            current_time: int = round(time.time())

            # If there are no messages in the cache, reset the time of last cache upload to now and sleep for 1 second. This means the timer will only start once new messaging activity has begun
            if not num_messages:
                self.time_last_message_backup = current_time
                await asyncio.sleep(1)
                continue

            time_since_last_message_upload: int = (
                current_time - self.time_last_message_backup
            )
            # If the number of stored messages is >= current active connections, or if there are any messages and the last upload was more than CACHED_MESSAGE_UPLOAD_TIMER seconds ago, do the batch upload immediately
            if num_messages >= max(len(self.active_connections), 5) or (
                time_since_last_message_upload > CACHED_MESSAGE_UPLOAD_TIMER
                and num_messages
            ):
                self.logger.info(
                    f"Upload cache triggered by cache size: {num_messages = }, {time_since_last_message_upload = }, {len(self.active_connections) = })"
                )
                await self.upload_cached_messages()
            await asyncio.sleep(1)

    async def upload_cached_messages(self):
        """Batch inserts all cached messages into database and resets upload timer"""
        if self.db.batch_insert_messages(self.message_cache):
            self.message_cache.clear()
            self.time_last_message_backup = round(time.time())
        else:
            # TODO log error on failure to avoid losing cached messages
            pass

    async def handle_perf_ping(self, message: dict):
        """Gather required performance data and send it to the monitor"""
        try:
            username = message.get("username")
            perf_test_id = message.get("perf_test_id")
            active_connections = len(self.active_connections)
            cpu_load = psutil.cpu_percent(interval=None, percpu=True)
            memory_usage = psutil.virtual_memory().percent
            # Calculate the time since the messave volume counter was set to 0, used to estimate a volume per second value. If the time interval is too low, set it to 0.25s to prevent excessively high numbers caused by dividing by values close to 0.
            mv_time_interval = time.perf_counter() - self.message_volume_timer
            if mv_time_interval < 0.25:
                mv_time_interval = 0.25

            # Update the EMA for message volume
            self.ema_message_volume = (
                self.alpha * (self.message_volume/mv_time_interval) + (1 - self.alpha) * self.ema_message_volume
            )

            # Calculate adjusted message rate
            # mv_adjusted = self.ema_message_volume

            response_message = {
                "event": "perf_test",
                "perf_test_id" : perf_test_id,
                "cpu_load" : cpu_load,
                "memory_usage" : memory_usage,
                "active_connections" : active_connections,
                "message_volume": self.message_volume,
                "mv_period": time.perf_counter() - self.message_volume_timer,
                # "mv_adjusted": round(self.message_volume / (time.perf_counter() - self.message_volume_timer)),
                "mv_adjusted": round(self.ema_message_volume)
            }
            websocket: WebSocket = self.active_connections.get(username).get("ws")
            self.message_volume = 0
            self.message_volume_timer = time.perf_counter()
            self.logger.debug(f"Sending perf response: {response_message}")
            await websocket.send_bytes(orjson.dumps(response_message))
        except Exception as e:
            self.logger.warning(f"Error sending perf response: {e}")




