import logging
from load_testing.load_tester import LoadTester


NUMBER_OF_TEST_ACCOUNTS = 100

NUM_ACTIONS = 20

CONNECTION_DELAY = None

logger = logging.getLogger('LoadTester')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter.datefmt = '%H:%M:%S'
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

load_tester = LoadTester(logger, NUMBER_OF_TEST_ACCOUNTS, NUM_ACTIONS, CONNECTION_DELAY)
load_tester.start()

# Not happy at 500, test lower
