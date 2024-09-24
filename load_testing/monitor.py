import time
import asyncio
import json
from json import JSONDecodeError
import orjson
import traceback
from pprint import pprint
from logging import Logger

from load_testing.virtual_user import User

class Monitor(User):
    def __init__(self, logger: Logger, account: dict):
        super().__init__(logger, account)
        self.perf_data: dict = {} #{channel:{} for channel in self.test_channels}
        self.perf_test_id = 0
        self.logger.info(f"Created: {self}")
        
        # Info to test/get from server:
        # message ping time
        # Server CPU load
        # Server memory usage
        # Server active accounts
        # Subscribers to that channel - ensure ping reply is sent to monitor after all other users in channel
        
    async def start_activity(self):
        self.logger.info("Monitor.start_activity()")
        # Join all channels, send message every X seconds, time how long until it returns. Maybe also join and leave channels and see how long it takes. Use a while True loop rather than X actions to ensure it is live throughout the entire test.
        # await self.match_test_channel_subscriptions()
        while self.connection_active:
            # for channel in self.channels:
            try:
                await self.send_perf_ping() #channel)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

    async def send_perf_ping(self): #, channel):
        """Send a message to the server with a request for server stats, and to measure response times"""
        message = {
                "event": "perf_test",
                "perf_test_id": self.perf_test_id
            }
        self.logger.debug(f"Sending: {message}")
        self.perf_data[self.perf_test_id] = {"latency": time.perf_counter()}
        await self.client_websocket.send_message(message)
        self.perf_test_id += 1


    async def handle_perf_response(self, message: dict):
        """Handle the perf test response message and log the data"""
        self.logger.debug(f"Monitor received: {message}")
        perf_test_id = message.get("perf_test_id")
        time_sent_at = self.perf_data[perf_test_id].get("latency")
        self.perf_data[perf_test_id] = {
            "perf_test_id" : perf_test_id,
            "latency": round(time.perf_counter() - time_sent_at, 4),
            "cpu_load" : message.get("cpu_load"),
            "memory_usage" : message.get("memory_usage"),
            "active_connections" : message.get("active_connections") - 1,
            "message_volume": message.get("message_volume"),
            "mv_period": message.get("mv_period", 0.0),
            "mv_adjusted": message.get("mv_adjusted", 0),
            }
        self.logger.debug(f"{self.perf_data[perf_test_id]=}")
        if message.get("active_connections") < 1:
            await self.logout()


    async def listen_for_messages(self):
        """Listen for perf test response messages"""
        self.logger.debug("Monitor listening for messages")
        while self.connection_active:
            try:
                # message_str = await self.client_websocket.websocket.recv()
                message_raw = await self.client_websocket.receive_message()
                self.logger.debug(f"Monitor received: {message_raw=}")
                if message_raw is not None:
                    try:
                        message: dict = orjson.loads(message_raw)
                    except JSONDecodeError as e:
                        self.logger.warning(f"JSONDecodeError: {e}: {message_raw=}")
                    event_type = message.get("event")
                    if event_type == "perf_test":
                        await self.handle_perf_response(message)
            except asyncio.CancelledError as e:
                pass 
            except Exception as e:
                if self.connection_active:
                    self.logger.warning(f"Monitor listener Exception: {self.connection_active=}, {e}", exc_info=True)
                    # traceback.print_tb(e.__traceback__)
                else:
                    self.logger.warning(f"Monitor listener Exception: {self.connection_active=}, {e}", exc_info=True)
                    break 

    async def match_test_channel_subscriptions(self):
        """Ensure monitor is connected to all test channels, and no other channels"""
        for channel in set(self.test_channels).union(self.channels):
            if channel not in self.channels:
                await self.join_channel(channel)
            elif channel not in self.test_channels:
                await self.leave_channel(channel)


    def __repr__(self):
        return f"Monitor({self.username=})"

