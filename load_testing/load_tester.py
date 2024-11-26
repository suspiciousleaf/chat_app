import json
import asyncio
import random
from logging import Logger
from os import getenv
import datetime

from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np

from load_testing.virtual_user import User
from load_testing.monitor import Monitor

load_dotenv()
MONITOR_USER = getenv("MONITOR_USER")
MONITOR_PASS = getenv("MONITOR_PASS")


test_channels = [f"test_{i}" for i in range(10)]


# Log in using usernames and passwords
with open("load_testing/accounts.json", "r") as f:
    accounts: dict = json.load(f)

# # Log in using bearer token
# with open("load_testing/accounts_tokens.csv", "r") as f:
    # accounts = [{"access_token":row["token"]} for row in csv.DictReader(f)]



class LoadTester:
    """Class to run load test by starting virtual users, logging performance data, and graphing the performance data across the run"""
    def __init__(self, logger: Logger, num_accounts: int, num_actions: int, delay_before_actions: int = 0, delay_between_actions: int = 2, connection_delay: float=0):
        self.logger: Logger = logger
        self.num_accounts: int = num_accounts
        self.test_account_pool: list = accounts
        self.active_accounts: list = []
        self.num_actions: int = num_actions
        self.delay_before_actions: int = delay_before_actions
        self.delay_between_actions: int = delay_between_actions
        self.connection_delay: float = connection_delay
        self.logger.info(f"Starting: {self}")
        self.monitor: Monitor = Monitor(self.logger, account={"username":MONITOR_USER, "password":MONITOR_PASS})

    def __repr__(self):
        return f"LoadTester({self.num_accounts=}, {self.num_actions=}, {self.connection_delay=}, {test_channels=})"

    async def create_and_run_user(self, account):
        """Create a virtual user and start its activity"""
        user = User(self.logger, account, actions=self.num_actions, delay_before_actions=self.delay_before_actions, delay_between_actions=self.delay_between_actions, test_channels=test_channels)
        self.logger.debug(f"Created: {user}")
        self.active_accounts.append(user)
        try:
            await user.run()
        except Exception as e:
            self.logger.warning(f"Error running user: {e}")
        finally:
            self.active_accounts.remove(user)

    async def run_load_test(self):
        """Begin the load test"""
        self.logger.debug(f"{len(self.test_account_pool)=}, {self.num_accounts=}")
        accounts_to_use = random.sample(sorted(self.test_account_pool), self.num_accounts) # sorted() used to convert dict to sequence
        tasks = []
        tasks.append(asyncio.create_task(self.monitor.run()))
        for i, account in enumerate(accounts_to_use):
            account = {"username": account,
                       "password": self.test_account_pool[account]}
            task = asyncio.create_task(self.create_and_run_user(account))
            tasks.append(task)
            if self.connection_delay:
                await asyncio.sleep(self.connection_delay)
        # Await completion of all load tasks, but not the monitor as its listener task runs indefinitely. User tasks stop their listener tasks automatically when they have completed their actions so this doesn't hinder gather.
        await asyncio.gather(*tasks[1:])
        await self.monitor.logout()


    def start(self):
        """Create an event loop and begin the load test"""
        try:
            asyncio.run(self.run_load_test())
            self.logger.info(f"LoadTester complete")
        except KeyboardInterrupt:
            self.logger.info("Load test cancelled by user")
        except Exception as e:
            self.logger.info(f"LoadTester.start() {type(e).__name__}: {e}")
        finally:
            try:
                self.process_results()
            except Exception as e:
                self.logger.warning(f"Unable to process performance data: {type(e).__name__}:{e}")

# Perf testing data format:
# {
#     "latency": float,
#     "perf_test_id" : int,
#     "cpu_load" : [float, float],
#     "memory_usage" : float,
#     "active_connections" : int,
#     "message_volume": int,
#     "mv_period": float,
#     "mv_adjusted": int,
# }

    def process_results(self):
        """Process the raw performance data, plot graphs, and save them"""
        latency = []
        perf_test_id = []
        cpu_load = []
        active_users = []
        message_volume = []
        if self.monitor.perf_data:
            self.logger.info("Raw data saved to: most_recent_perf_raw_data.json")

            # Rolling save of raw data from most recent run so it can be checked in case of exceptions below
            with open("most_recent_perf_raw_data.json", "w") as f:
                json.dump(self.monitor.perf_data, f)

            for data_point in self.monitor.perf_data.values():
                try:
                    # # 0 values must be ignored to calculate best fit curve
                    if max(data_point["cpu_load"]) < 3 or not data_point["active_connections"]:
                        continue
                    latency.append(data_point["latency"])
                    perf_test_id.append(data_point["perf_test_id"])
                    cpu_load.append(max(data_point["cpu_load"]))
                    active_users.append(data_point["active_connections"])
                    message_volume.append(int(data_point["mv_adjusted"]))
                except KeyError:
                    continue

            # Create a figure with 4 subplots
            fig, axs = plt.subplots(2, 2, figsize=(12, 12))
            
            # First subplot: CPU Load vs Latency
            axs[0, 0].scatter(cpu_load, message_volume, color='#008fde')
            axs[0, 0].set_xlabel('CPU Load (%)')
            axs[0, 0].set_ylabel('Message Volume', color='#008fde')
            axs[0, 0].tick_params(axis='y', labelcolor='#008fde')

            # Create a second y-axis on the right
            ax1 = axs[0, 0].twinx()

            # Plot message_volume vs cpu_load on the right y-axis
            ax1.scatter(cpu_load, latency, color='#a16ae8', label='Latency (s)')
            ax1.set_ylabel('Latency (s)', color='#a16ae8')
            ax1.tick_params(axis='y', labelcolor='#a16ae8')

            # Second subplot: Active Users vs Message Volume
            axs[0, 1].scatter(perf_test_id, message_volume, color='#008fde', label='Message Volume')
            axs[0, 1].set_xlabel('perf_test_id')
            axs[0, 1].set_ylabel('Message Volume', color='#008fde')
            axs[0, 1].tick_params(axis='y', labelcolor='#008fde')
            # Create a second y-axis on the right
            ax2 = axs[0, 1].twinx()

            # Plot cpu_load vs perf_test_id on the right y-axis
            ax2.scatter(perf_test_id, cpu_load, color='#a16ae8', label='CPU Load')
            ax2.set_ylabel('CPU Load (%)', color='#a16ae8')
            ax2.tick_params(axis='y', labelcolor='#a16ae8')

            # Third subplot: Active Users vs CPU Load
            axs[1, 0].scatter(active_users, message_volume, color='#008fde')
            axs[1, 0].set_xlabel('Active Users')
            axs[1, 0].set_ylabel('Message Volume', color='#008fde')
            axs[1, 0].tick_params(axis='y', labelcolor='#008fde')
            # Create a second y-axis on the right
            ax3 = axs[1, 0].twinx()

            # Plot cpu_load vs perf_test_id on the right y-axis
            ax3.scatter(active_users, cpu_load, color='#a16ae8', label='CPU Load (%)')
            ax3.set_ylabel('CPU Load (%)', color='#a16ae8')
            ax3.tick_params(axis='y', labelcolor='#a16ae8')

            # Create a boxplot for the final graph, requires some additional calculations
            # Convert message_volume and latency to NumPy arrays
            message_volume = np.array(message_volume)
            latency = np.array(latency)

            num_bins = 10
            bins = np.linspace(min(message_volume), max(message_volume), num_bins + 1)  # num_bins + 1 to account for bin edges


            latency_groups = [latency[(message_volume >= bins[i]) & (message_volume < bins[i+1])] for i in range(num_bins)]
            latency_groups[-1] = latency[(message_volume >= bins[-2]) & (message_volume <= bins[-1])]


            axs[1, 1].boxplot(latency_groups, patch_artist=True)

            axs[1, 1].set_xlabel('Message Volume Bins')
            axs[1, 1].set_ylabel('Latency (s)')
            axs[1, 1].set_ylim(0, 2.5)

            axs[1, 1].set_xticklabels([f'{int(bins[i])}-{int(bins[i+1])}' for i in range(num_bins)], rotation=45)

            # Adjust layout and display both plots
            plt.tight_layout()

            percentile_90 = round(np.percentile(latency, 90)*1000)
            percentile_95 = round(np.percentile(latency, 95)*1000)
            percentile_99 = round(np.percentile(latency, 99)*1000)

            print(f"90th: {percentile_90}ms")
            print(f"95th: {percentile_95}ms")
            print(f"99th: {percentile_99}ms")

            current_date = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
            file_name = f"{current_date},pb,uvloop,percentiles_ms=[{percentile_90},{percentile_95},{percentile_99}],accounts={self.num_accounts},actions={self.num_actions},delay_before_act={self.delay_before_actions},delay_between_act={self.delay_between_actions},delay_between_connections={self.connection_delay}"
            # Save the figure
            plt.savefig(f'perf_data/{file_name}.png', dpi=300)  # Save as PNG with high resolution (300 dpi)

            with open(f"perf_data/{file_name}.json", "w") as f:
                json.dump(self.monitor.perf_data, f)

            plt.show()
        else:
            self.logger.warning("No performance data recorded")