import time
import asyncio
import datetime
from logging import Logger
import cProfile
import os
from os import getenv

from pathlib import Path
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from dotenv import load_dotenv
import psutil

from google.protobuf.message import EncodeError, DecodeError
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.internal import api_implementation

print(f"Protobuf using C++ serialization: {api_implementation.Type() == 'upb'}")

try:
    from services.db_manager import DatabaseManager
    import message_pb2
except:
    from server.services.db_manager import DatabaseManager
    from server import message_pb2



env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)

# REDIS_QUEUE = getenv("REDIS_QUEUE")
MAX_RECONNECT_ATTEMPTS = int(getenv("MAX_RECONNECT_ATTEMPTS"))
RECONNECT_DELAY = getenv("RECONNECT_DELAY")
CACHED_MESSAGE_UPLOAD_TIMER = int(getenv("CACHED_MESSAGE_UPLOAD_TIMER"))
USE_CPROFILE = getenv("USE_CPROFILE") == "True"


class ConnectionManager:
    """
    Manages WebSocket connections, channels, and message broadcasting for a chat application.

    Attributes:
        logger (Logger): Logger instance for debugging and error reporting.
        db (DatabaseManager): Handles database interactions.
        listener_task (asyncio.Task): Background task for handling cached messages.
        active_connections (dict): Tracks active WebSocket connections and their subscribed channels.
        channel_subscribers (dict): Maps channels to their active subscribers.
        message_cache (list): Stores messages temporarily before uploading to the database.
        time_last_message_backup (int): Timestamp of the last message cache upload.
        load_testing (bool): Indicates if the server is under load testing.
        ema_window (int): Window size for exponential moving average calculations.
        alpha (float): Smoothing factor for exponential moving average.
        run_profiling (bool): Whether cProfile is enabled for performance profiling.
        pr (cProfile.Profile | None): cProfile instance for profiling.
    """
    def __init__(self, logger:Logger, db: DatabaseManager):
        """
        Initializes the ConnectionManager.

        Args:
            logger (Logger): Logger instance.
            db (DatabaseManager): Database manager for handling database operations.
        """
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
        self.message_volume = 0
        self.message_volume_timer = None
        self.ema_window = 3
        self.alpha = 2 / (self.ema_window + 1)  # Smoothing factor based on window size
        self.run_profiling: bool = USE_CPROFILE
        self.pr: cProfile.Profile | None = None
        

    async def connect(self, websocket: WebSocket, username: str):
        """
        Establishes a WebSocket connection and subscribes the user to their channels.

        Args:
            websocket (WebSocket): The WebSocket connection instance.
            username (str): The username of the connecting client.
        """
        await websocket.accept()
        channels: set = self.db.retrieve_channels(username)
        self.active_connections[username] = {"ws": websocket, "channels": channels}
        for channel in channels:
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = {}
            self.channel_subscribers[channel][username] = websocket
        if username == "monitor":
            if self.run_profiling:
                self.start_profiling()
            self.logger.info("Load testing beginning")
            self.load_testing = True
            # Reset load testing values
            self.message_volume = 0
            self.message_volume_timer = time.perf_counter()
            self.ema_message_volume = 0
            
        else:
            await self.send_channel_subscriptions(websocket, channels)
            # Channel message history is currently disabled
            # await self.send_channel_history(websocket, channels)

        # Starts the message listener once at least one user is connected.
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.start_listener())
            self.logger.info("First connection opened, starting listener")

        self.logger.info(f"Active connections: {len(self.active_connections)}")

    async def send_channel_subscriptions(self, websocket: WebSocket, channels: set):
        """
        Sends a list of the user's channel subscriptions.

        Args:
            websocket (WebSocket): The WebSocket instance to send the message to.
            channels (set): Set of channel names the user is subscribed to.
        """

        message_data: dict = {"event": "channel_subscriptions", "data": list(channels)}
        message_bytes: bytes = self.encode_message(message_data)
        await self.send_bytes_message(websocket, message_bytes)

    async def send_bytes_message(self, websocket: WebSocket, message_bytes: bytes):
        """
        Sends a binary message over the WebSocket.

        Args:
            websocket (WebSocket): The WebSocket connection to send the message to.
            message_bytes (bytes): The binary message data.
        """
        if message_bytes is not None:
            await websocket.send_bytes(message_bytes)

    def encode_message(self, message_data: dict) -> bytes:
        """
        Encodes a message into a binary format using protobuf.

        Args:
            message_data (dict): The message data to encode.

        Returns:
            bytes: The encoded message.
        """
        try:
            message_object = ParseDict(message_data, message_pb2.ChatMessage())

            return message_object.SerializeToString()
        except EncodeError as e:
            self.logger.warning(f"encode_message() Protobuf EncodeError: {e}")
        except Exception as e:
            self.logger.warning(f"Exception during encode_message(): {type(e).__name__}: {e}")

    #! This is still written for orjson, needs updating to use with protobuf if required
    # async def send_channel_history(self, websocket: WebSocket, channels: set):
    #     """Send the message history for all subscribed channels to the client"""
    #     message_history: list = self.db.retrieve_message_history(channels)

    #     # If any messages are in the cache, add the to the message history to send to newly logged in accounts
    #     if self.message_cache:
    #         for message in self.message_cache:
    #             if message.get("channel") in channels:
    #                 message_history.extend(message)

    #     # history_message = {"event": "message history", "data": message_history}

    #     # # await websocket.send_bytes(orjson.dumps(history_message))
    #     # await self.websocket_send_bytes(websocket, history_message)


    #     # Message history can exceed the maximum size for a websocket message (1MB), so the section below checks the size and breaks it down into multiple messages if it exceeds this limit. Currently not very performant as it serializes each message twice
    #     #! Size count is broken by using orjson or protobuf
    #     history_message = {"event": "message history", "data": []}
    #     max_size = 1024 * 900  # 1 MB size limit for websocket message, with an allowance for getsizeof inaccurate estimate

    #     current_size = 0

    #     for message in message_history:
    #         message_size = getsizeof(orjson.dumps(message))

    #         if current_size + message_size > max_size:
    #             # await websocket.send_bytes(orjson.dumps(history_message))
    #             await self.encode_send_message(websocket, message_history)
    #             # Reset for the next chunk
    #             history_message["data"] = []
    #             current_size = 0

    #         history_message["data"].append(message)
    #         current_size += message_size

    #     # Send any remaining messages
    #     if history_message["data"]:
    #         # await websocket.send_bytes(orjson.dumps(history_message))
    #         await self.encode_send_message(websocket, message_history)

    async def leave_channel(self, username: str, channel: str):
        """
        Removes the user from a channel subscription.

        Args:
            username (str): The username of the user leaving the channel.
            channel (str): The name of the channel to leave.
        """
        self.db.remove_channel(username, channel)
        # Check channel is present in list of active users and channel subscriptions, and remove it
        if channel in self.active_connections[username]["channels"]:
            self.active_connections[username]["channels"].remove(channel)
        if username in self.channel_subscribers[channel]:
            self.channel_subscribers[channel].pop(username)

    async def add_channel(self, username, channel: str):
        """
        Subscribes a user to a new channel.

        Args:
            username (str): The username of the user.
            channel (str): The name of the channel to subscribe to.
        """
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
        """
        Handles user disconnection, unsubscribing them from channels and closing the connection. If user is Monitor, stop monitoring.

        Args:
            username (str): The username of the disconnecting user.
        """
        if username == "monitor":
            self.load_testing = False
            self.logger.info("Stopped load testing")
            self.message_volume = 0
            self.message_volume_timer = None
            self.ema_message_volume = 0
            if self.run_profiling:
                self.stop_profiling()

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
        """
        Sends a message to all clients subscribed to a specific channel.

        Args:
            message (dict): The message data to broadcast.
        """
        channel = message.get("channel")
        closed_connections = []
        tasks = []

        message_bytes: bytes = self.encode_message(message)
        # Iterate over users and websockets subscribed to the channel
        for user, websocket in self.channel_subscribers.get(channel, {}).items():
            # Append the send_message task to the list of tasks
            tasks.append(self.send_message(user, websocket, message_bytes, closed_connections))
        
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


    async def send_message(self, user: str, websocket: WebSocket, message_bytes: bytes, closed_connections: list):
        """
        Sends a message to a specific user.

        Args:
            user (str): The username of the recipient.
            websocket (WebSocket): The WebSocket connection for the user.
            message_bytes (bytes): The binary message data.
            closed_connections (list): List of users with closed connections.
        """
        if user not in self.active_connections:
            return
        try:
            await self.send_bytes_message(websocket, message_bytes)
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
                self.logger.warning(f"Exception sending message, closing connection: {user in self.active_connections=} {type(e).__name__}: {e}", exc_info=True)
                closed_connections.append(user)

    def decode_message(self, message_bytes: bytes) -> dict:
        """
        Decodes a binary message using protobuf.

        Args:
            message_bytes (bytes): The binary message data.

        Returns:
            dict: The decoded message data.
        """
        try:
            parsed_message = message_pb2.ChatMessage()
            parsed_message.ParseFromString(message_bytes)

            if parsed_message.event == "perf_test":
                return {
                    "event": "perf_test",
                    "perf_test_id": parsed_message.perf_test_id
                    }

            message_dict = {
                "event": parsed_message.event,
                "channel": parsed_message.channel,
                }

            if message_dict.get("event") == "message":
                message_dict["content"] = parsed_message.content
                # Timestamp is generated by server for UTC and converted to an ISO 8601 format string for database compatibility
                message_dict["sent_at"] = self.db.adapt_datetime_iso(
                        datetime.datetime.now(datetime.timezone.utc)
                    )
            return message_dict
        except Exception as e:
            raise DecodeError(e)


    async def handle_incoming_message(self, message_bytes: bytes, username: str):
        """
        Processes an incoming message and handles the appropriate action.

        Args:
            message_bytes (bytes): The binary message data.
            username (str): The username of the sender.
        """
        try:
            message: dict = self.decode_message(message_bytes)
            message["username"] = username
            if message.get("event") == "message":
                await self.broadcast(message)
                self.message_cache.append(message)
                # TODO Add graceful error handling for batch inserts / fails
            elif message.get("event") == "leave_channel":
                await self.leave_channel(username, message.get("channel"))
            elif message.get("event") == "add_channel":
                await self.add_channel(username, message.get("channel"))
            elif message.get("event") == "perf_test":
                await self.handle_perf_ping(message)
        except DecodeError as e:
            self.logger.warning(f"handle_incoming_message() Protobuf DecodeError: {e}")
        except KeyError:
            pass
        except Exception as e:
            self.logger.warning(f"Exception during handle_incoming_message(): {type(e).__name__}: {e}")


    async def start_listener(self):
        """
        Starts a background task to monitor and handle cached messages.
        """
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
        """
        Uploads cached messages to the database in batch mode.
        """
        if self.db.batch_insert_messages(self.message_cache):
            self.message_cache.clear()
            self.time_last_message_backup = round(time.time())
        else:
            # TODO log error on failure to avoid losing cached messages
            pass

    async def handle_perf_ping(self, message: dict):
        """
        Handles performance test pings and sends back performance metrics.

        Args:
            message (dict): The performance test message data.
        """
        try:
            username = message.get("username")
            perf_test_id = message.get("perf_test_id")
            active_connections = len(self.active_connections)
            cpu_load = psutil.cpu_percent(interval=None, percpu=True)
            memory_usage = psutil.virtual_memory().percent
            # Calculate the time since the message volume counter was set to 0, used to estimate a volume per second value. If the time interval is too low, set it to 0.25s to prevent excessively high numbers caused by dividing by values close to 0.
            mv_time_interval = time.perf_counter() - self.message_volume_timer
            if mv_time_interval < 0.25:
                mv_time_interval = 0.25

            # Update the EMA for message volume
            self.ema_message_volume = (
                self.alpha * (self.message_volume/mv_time_interval) + (1 - self.alpha) * self.ema_message_volume
            )

            response_message = {
                "event": "perf_test",
                "perf_test_id" : perf_test_id,
                "cpu_load" : cpu_load,
                "memory_usage" : memory_usage,
                "active_connections" : active_connections,
                "message_volume": self.message_volume,
                "mv_period": time.perf_counter() - self.message_volume_timer,
                "mv_adjusted": round(self.ema_message_volume)
            }
            websocket: WebSocket = self.active_connections.get(username).get("ws")
            self.message_volume = 0
            self.message_volume_timer = time.perf_counter()
            self.logger.debug(f"Sending perf response: {response_message}")
            # await websocket.send_bytes(orjson.dumps(response_message))
            message_bytes = self.encode_message(response_message)
            await self.send_bytes_message(websocket, message_bytes)
        except Exception as e:
            self.logger.warning(f"Error sending perf response: {e}")

    def start_profiling(self):
        """
        Starts the cProfile performance profiling.
        """
        self.pr = cProfile.Profile()
        self.pr.enable()

    def stop_profiling(self):
        """
        Stops cProfile and saves profiling data to a file.
        """
        self.pr.disable()
        current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        if "Programming" not in os.getcwd():
            try:
                profile_dir = os.path.join("services", "db_data", "profiles")
                os.makedirs(profile_dir, exist_ok=True)
                profile_file = os.path.join(profile_dir, f"{current_date}.prof")
                self.pr.dump_stats(profile_file)
            except:
                print("Failed to save cProfile file")
        else:
            self.pr.dump_stats(fr"C:\Users\David\Documents\Programming\Python\Code_list\Projects\chat_app\chat_app\server\services\db_data\profiles\{current_date}.prof")
        self.pr = None


