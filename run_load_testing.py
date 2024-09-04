from load_testing.load_tester import LoadTester


NUMBER_OF_TEST_ACCOUNTS = 30

NUM_ACTIONS = 20

CONNECTION_DELAY = 0.5

load_tester = LoadTester(NUMBER_OF_TEST_ACCOUNTS, NUM_ACTIONS, CONNECTION_DELAY)
load_tester.start()

# Not happy at 500, test lower
