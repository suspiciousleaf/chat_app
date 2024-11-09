import time
import threading

from tqdm import trange

import logging
from load_testing.load_tester import LoadTester


NUM_ACCOUNTS = 425

NUM_ACTIONS = 40

CONNECTION_DELAY = 0.35 
# CONNECTION_DELAY = 0

DELAY_BEFORE_ACTION = NUM_ACCOUNTS * CONNECTION_DELAY
# DELAY_BEFORE_ACTION = 0
DELAY_BETWEEN_ACTIONS = 6

run_time = int(DELAY_BEFORE_ACTION + (NUM_ACTIONS * DELAY_BETWEEN_ACTIONS) + (NUM_ACCOUNTS * CONNECTION_DELAY))

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logger = logging.getLogger('LoadTester')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter.datefmt = '%H:%M:%S'
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

load_tester = LoadTester(logger, NUM_ACCOUNTS, NUM_ACTIONS, DELAY_BEFORE_ACTION, DELAY_BETWEEN_ACTIONS, CONNECTION_DELAY)

def progress_bar():
    """Function to display a progress bar"""
    for _ in trange(run_time, desc="Load Test Progress", unit="s"):
        time.sleep(1) 

# Run progress bar in a separate thread
progress_bar_thread = threading.Thread(target=progress_bar)
progress_bar_thread.start()

load_tester.start()
