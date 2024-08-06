import asyncio
import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server
import logging
import sys


SERVER_FILENAME = "server"


def configure_logging():
    # Configure root logger
    logging.getLogger().setLevel(logging.WARNING)

    # Configure uvicorn loggers
    logging.getLogger("uvicorn").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.ERROR)

    # Create a null handler to discard logs
    null_handler = logging.NullHandler()

    # Attach the null handler to the uvicorn loggers
    logging.getLogger("uvicorn").addHandler(null_handler)
    logging.getLogger("uvicorn.error").addHandler(null_handler)
    logging.getLogger("uvicorn.access").addHandler(null_handler)

    # Remove any existing handlers from the root logger
    for handler in logging.getLogger().handlers:
        logging.getLogger().removeHandler(handler)

    # Add a StreamHandler to the root logger that only shows WARNING and above
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


def run():
    # Explicitly set the ProactorEventLoop for Windows
    if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # configure_logging()

    config = Config(
        "server:app", host="127.0.0.1", port=8000, log_level="warning", reload=True
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    run()
