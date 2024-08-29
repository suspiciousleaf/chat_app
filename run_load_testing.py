from load_testing.load_tester import LoadTester

NUMBER_OF_TEST_ACCOUNTS = 100

NUM_ACTIONS = 20

CONNECTION_DELAY = 0.25

load_tester = LoadTester(NUMBER_OF_TEST_ACCOUNTS, NUM_ACTIONS, CONNECTION_DELAY)
load_tester.start()
