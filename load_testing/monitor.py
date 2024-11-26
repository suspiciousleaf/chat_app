import time
import asyncio
import traceback
from pprint import pprint
from logging import Logger

from load_testing.virtual_user import User

class Monitor(User):
    """Monitor object to send pings to the server for performance metrics and store the data"""
    def __init__(self, logger: Logger, account: dict):
        super().__init__(logger, account)
        self.perf_data: dict = {}
        self.perf_test_id = 1
        self.logger.info(f"Created: {self}")
        
        # Info to test/get from server:
        # Message latency
        # Server CPU load
        # Server memory usage
        # Server active accounts
        
    async def start_activity(self):
        """Begin sending pings, once per second"""
        self.logger.info("Monitor.start_activity()")
        while self.connection_active:
            try:
                await self.send_perf_ping()
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
                message = await self.client_websocket.receive_message()
                self.logger.debug(f"Monitor received: {message=}")
                if message is not None:
                    event_type = message.get("event")
                    if event_type == "perf_test":
                        await self.handle_perf_response(message)
            except asyncio.CancelledError as e:
                pass 
            except Exception as e:
                self.logger.warning(message)
                if self.connection_active:
                    self.logger.warning(f"Monitor listener Exception: {self.connection_active=}, {e}", exc_info=True)
                    # traceback.print_tb(e.__traceback__)
                else:
                    self.logger.warning(f"Monitor listener Exception: {self.connection_active=}, {e}", exc_info=True)
                    break 


    def __repr__(self):
        return f"Monitor({self.username=})"

