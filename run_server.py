# import asyncio
import os

from uvicorn.config import Config
from uvicorn.server import Server
import winloop


SERVER_FILENAME = "server.main_server"

def run():
    winloop.install()
    # # Explicitly set the ProactorEventLoop for Windows
    # if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    #     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # # configure_logging()
    os.chdir(r"C:\Users\David\Documents\Programming\Python\Code_list\Projects\chat_app\chat_app\server")
    config = Config(
        f"{SERVER_FILENAME}:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        reload=False,
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Server shut down")