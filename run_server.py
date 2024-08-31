import asyncio
import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server
import logging
import sys


SERVER_FILENAME = "server.main_server"


def run():
    # Explicitly set the ProactorEventLoop for Windows
    if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # configure_logging()

    config = Config(
        f"{SERVER_FILENAME}:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        reload=False,
        reload_includes=["*.py", ".env"],
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Server shut down")
