import json
import numpy as np

with open("perf_data/2024-09-19_15-58-47-self.num_accounts=250,self.num_actions=40,self.connection_delay=0.25.json", "r") as f:
    raw_data = json.load(f)


latencies = [raw_data[ping_id]["latency"] for ping_id in raw_data]

# Calculate the 95th and 99th percentiles
percentile_90 = np.percentile(latencies, 90)
percentile_95 = np.percentile(latencies, 95)
percentile_99 = np.percentile(latencies, 99)

print(f"90th: {percentile_90*1000:.0f}ms")
print(f"95th: {percentile_95*1000:.0f}ms")
print(f"99th: {percentile_99*1000:.0f}ms")


