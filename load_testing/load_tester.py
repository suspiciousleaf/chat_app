import json
import asyncio
import threading
import random
import csv
from logging import Logger
from os import getenv
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np
import datetime

from load_testing.virtual_user import User
from load_testing.monitor import Monitor

load_dotenv()
MONITOR_USER = getenv("MONITOR_USER")
MONITOR_PASS = getenv("MONITOR_PASS")


test_channels = [f"test_{i}" for i in range(10)]


# Log in using username and password
with open("load_testing/accounts.json", "r") as f:
    accounts: dict = json.load(f)

# # Log in using bearer token
# with open("load_testing/accounts_tokens.csv", "r") as f:
    # accounts = [{"access_token":row["token"]} for row in csv.DictReader(f)]



class LoadTester:
    def __init__(self, logger: Logger, num_accounts, num_actions, connection_delay=None):
        self.logger: Logger = logger
        self.num_accounts = num_accounts
        self.test_account_pool: list = accounts
        self.active_accounts = []
        self.num_actions = num_actions
        self.connection_delay: float | None = connection_delay
        self.logger.info(f"Starting: {self}")
        self.monitor: Monitor = Monitor(self.logger, account={"username":MONITOR_USER, "password":MONITOR_PASS})

    def __repr__(self):
        return f"LoadTester({self.num_accounts=}, {self.num_actions=}, {self.connection_delay=}, {test_channels=})"

    async def create_and_run_user(self, account):
        user = User(self.logger, account, actions=self.num_actions, test_channels=test_channels)
        self.logger.debug(f"Created: {user}")
        self.active_accounts.append(user)
        try:
            await user.run()
        except Exception as e:
            self.logger.warning(f"Error running user: {e}")
        finally:
            self.active_accounts.remove(user)

    async def run_load_test(self):
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
                delay = self.connection_delay
                if i > len(accounts_to_use) / 2:
                    delay *= 2
                await asyncio.sleep(self.connection_delay)
        # Await completion of all load tasks, but not the monitor as its listener task runs indefinitely
        await asyncio.gather(*tasks[1:])
        await self.monitor.logout()


    def start(self):
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
        latency = []
        perf_test_id = []
        cpu_load = []
        active_users = []
        message_volume = []
        if self.monitor.perf_data:
            self.logger.info("Raw data saved to: most_recent_perf_raw_data.json")

            with open("most_recent_perf_raw_data.json", "w") as f:
                json.dump(self.monitor.perf_data, f)

            for data_point in self.monitor.perf_data.values():
                try:
                    # 0 values must be ignored to calculate best fit curve
                    if not data_point["mv_adjusted"] or not data_point["active_connections"] or max(data_point["cpu_load"]) < 3:
                        continue
                    latency.append(data_point["latency"])
                    perf_test_id.append(data_point["perf_test_id"])
                    # for load in data_point["cpu_load"]:
                    #     cpu_load.append(load)
                    cpu_load.append(max(data_point["cpu_load"]))
                    active_users.append(data_point["active_connections"])
                    message_volume.append(int(data_point["mv_adjusted"]))
                except KeyError:
                    continue

            # self.logger.info(list(zip(active_users, message_volume)))

            # Create a figure with 2 subplots
            fig, axs = plt.subplots(2, 2, figsize=(12, 12))
            
            # First subplot: CPU Load vs Latency
            axs[0, 0].scatter(cpu_load, message_volume)
            axs[0, 0].set_xlabel('CPU Load (%)')
            axs[0, 0].set_ylabel('Message Volume', color='blue')
            axs[0, 0].tick_params(axis='y', labelcolor='blue')
            # axs[0, 0].set_title('CPU Load vs Latency')

            # Create a second y-axis on the right
            ax1 = axs[0, 0].twinx()

            # Plot message_volume vs cpu_load on the right y-axis
            ax1.scatter(cpu_load, latency, color='red', label='Latency (s)')
            ax1.set_ylabel('Latency (s)', color='red')
            ax1.tick_params(axis='y', labelcolor='red')

            # Second subplot: Active Users vs Message Volume
            axs[0, 1].scatter(perf_test_id, message_volume, color='blue', label='Message Volume')
            axs[0, 1].set_xlabel('perf_test_id')
            axs[0, 1].set_ylabel('Message Volume', color='blue')
            axs[0, 1].tick_params(axis='y', labelcolor='blue')

            # Create a second y-axis on the right
            ax2 = axs[0, 1].twinx()

            # Plot cpu_load vs perf_test_id on the right y-axis
            ax2.scatter(perf_test_id, cpu_load, color='red', label='CPU Load')
            ax2.set_ylabel('CPU Load (%)', color='red')
            ax2.tick_params(axis='y', labelcolor='red')

            # Optional: add a title to the subplot
            axs[0, 1].set_title('Performance Test: Message Volume and CPU Load')

            # Third subplot: Active Users vs CPU Load
            axs[1, 0].scatter(active_users, message_volume)
            axs[1, 0].set_xlabel('Active Users')
            axs[1, 0].set_ylabel('Message Volume', color='blue')
            axs[1, 0].tick_params(axis='y', labelcolor='blue')
            # axs[1, 0].set_title('CPU Load vs Message Volume')

            # Create a second y-axis on the right
            ax3 = axs[1, 0].twinx()

            # Plot cpu_load vs perf_test_id on the right y-axis
            ax3.scatter(active_users, cpu_load, color='red', label='CPU Load (%)')
            ax3.set_ylabel('CPU Load (%)', color='red')
            ax3.tick_params(axis='y', labelcolor='red')

            # Fourth subplot: Message Volume vs Latency
            axs[1, 1].scatter(message_volume, latency)
            axs[1, 1].set_xlabel('Message Volume')
            axs[1, 1].set_ylabel('Latency (s)')
            # axs[1, 1].set_title('Message Volume vs Latency')

            # # Best fit line
            # poly_coeffs = np.polyfit(active_users, message_volume, 2)  
            # poly_func = np.poly1d(poly_coeffs)
            # x = np.linspace(min(active_users), max(active_users), 100)
            # y = poly_func(x)
            # axs[1].plot(x, y, color='red', label='Best Fit Curve') 

            #! axs[1].legend()

            # # First subplot: Active Users vs Message Volume (normal scale)
            # axs[0].scatter(active_users, message_volume)
            # axs[0].set_xlabel('Active Users')
            # axs[0].set_ylabel('Message Volume')
            # axs[0].set_title('Active Users vs Message Volume')

            # # Best fit line for normal graph (quadratic fit)
            # poly_coeffs = np.polyfit(active_users, message_volume, 2)  # 2nd degree polynomial fit
            # poly_func = np.poly1d(poly_coeffs)  # Create the polynomial function

            # # Generate values for the best-fit curve
            # x = np.linspace(min(active_users), max(active_users), 100)
            # y = poly_func(x)

            # # Plot the best-fit curve on the first subplot
            # axs[0].plot(x, y, color='red', label='Best Fit Curve')
            # axs[0].legend()

            # # Second subplot: Active Users vs Log(Message Volume)
            # log_message_volume = np.log(message_volume)  # Log-transform the message volume
            # axs[1].scatter(active_users, log_message_volume)
            # axs[1].set_xlabel('Active Users')
            # axs[1].set_ylabel('Log(Message Volume)')
            # axs[1].set_title('Active Users vs Log(Message Volume)')

            # # Best fit line for log-transformed data (linear fit)
            # log_poly_coeffs = np.polyfit(active_users, log_message_volume, 1)  # Linear fit
            # log_poly_func = np.poly1d(log_poly_coeffs)

            # # Generate the best-fit line for the log-transformed data
            # y_log_fit = log_poly_func(x)

            # # Plot the best-fit line on the second subplot
            # axs[1].plot(x, y_log_fit, color='red', label=f'Best Fit Line (y = {log_poly_coeffs[0]:.2f}x + {log_poly_coeffs[1]:.2f})')
            # axs[1].legend()


            # Adjust layout and display both plots
            plt.tight_layout()
            current_date = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_name = f"{current_date}-{self.num_accounts=},{self.num_actions=},{self.connection_delay=}"
            # Save the figure
            plt.savefig(f'perf_data/{file_name}.png', dpi=300)  # Save as PNG with high resolution (300 dpi)

            plt.show()
        else:
            self.logger.warning("No performance data recorded")