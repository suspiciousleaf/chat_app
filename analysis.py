# Run this to do analysis on data from completed runs

import json
import logging

import numpy as np

from load_testing.load_tester import LoadTester

with open("perf_data/2024-09-20_13-57,percentiles_ms=[202,246,310],accounts=250,actions=40,delay_before_act=60,delay_between_act=6,delay_between_connections=0.25.json", "r") as f:
    raw_data = json.load(f)


logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logger = logging.getLogger('LoadTester')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter.datefmt = '%H:%M:%S'
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

NUMBER_OF_TEST_ACCOUNTS = 250

NUM_ACTIONS = 40

CONNECTION_DELAY = 0.25
# CONNECTION_DELAY = None

DELAY_BEFORE_ACTION = 60
DELAY_BETWEEN_ACTIONS = 6

load_tester = LoadTester(logger, NUMBER_OF_TEST_ACCOUNTS, NUM_ACTIONS, DELAY_BEFORE_ACTION, DELAY_BETWEEN_ACTIONS, CONNECTION_DELAY)

load_tester.monitor.perf_data = raw_data
load_tester.process_results()

