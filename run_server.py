import asyncio
from uvicorn.config import Config
from uvicorn.server import Server
import logging
import sys
import cProfile
import pstats
import io
import datetime


SERVER_FILENAME = "server.main_server"

USE_cPROFILE = True


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
        # reload_includes=["*.py", ".env"],
    )
    server = Server(config)
    server.run()


if __name__ == "__main__":
    try:
        if USE_cPROFILE:
            pr = cProfile.Profile()
            pr.enable()
        run()
    except KeyboardInterrupt:
        print("Server shut down")
    finally:
        if USE_cPROFILE:
            pr.disable()
            # pr.print_stats()

            # Create a stream to capture the profile output
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)

            # Print time spent in functions (not including sub-functions)
            print("\nTime spent in function:")
            ps.sort_stats('time').print_stats(20)

            # Clear the string for cumulative stats
            s.truncate(0)
            s.seek(0)

            # Print cumulative time spent in functions (including sub-functions)
            print("\nTime spent in function, including in sub-functions:")
            ps.sort_stats('cumulative').print_stats(20)

            # # Output the profiling results
            # print(s.getvalue())
            current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

            pr.dump_stats(fr"C:\Users\David\Documents\Programming\Python\Code_list\Projects\chat_app\chat_app\load_testing\{current_date}_output.prof")
        else:
            pass
