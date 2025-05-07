# AI: ChatGPT 4o
# prompt: help  me with some starter code to run testclient.py 5 times with different p values [0.0, 0.2, 0.4, 0.6, 0.8],  aand save the output to a csv file.  The output should be saved in a csv file  in the same directory as this script.
import subprocess
import sys
import time
import glob
import csv
import re
import matplotlib.pyplot as plt
import pandas as pd

p_values = [0.0, 0.2, 0.4, 0.6, 0.8]
csv_file = "latency_results.csv"

# Clear previous CSV
with open(csv_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["p_value", "lookup_latency", "trade_latency", "order_latency"])

for p in p_values:
    print(f"\n--- Running clients for p = {p} ---")
    processes = []
    for i in range(5):
        log_file = open(f"client_{i}_p{str(p).replace('.', '')}.log", "w")
        proc = subprocess.Popen(
            ["python", "testclient.py", str(p)],
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        processes.append((proc, log_file))

    for proc, log_file in processes:
        proc.wait()
        log_file.close()

    # Parse latency files
    latency_files = glob.glob("latency_*.txt")
    lookup_sum = trade_sum = order_sum = 0
    count = 0
    for file in latency_files:
        with open(file, "r") as f:
            content = f.read()
            try:
                lookup = float(re.search(r"lookup latency: ([0-9.]+)", content).group(1))
                trade = float(re.search(r"trade latency: ([0-9.]+)", content).group(1))
                order = float(re.search(r"order latency: ([0-9.]+)", content).group(1))
                lookup_sum += lookup
                trade_sum += trade
                order_sum += order
                count += 1
            except Exception:
                print(f"Warning: Could not parse {file}")

    if count > 0:
        lookup_avg = lookup_sum / count
        trade_avg = trade_sum / count
        order_avg = order_sum / count

        # Append to CSV
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([p, lookup_avg, trade_avg, order_avg])

        print(f"Averages for p = {p} | Lookup: {lookup_avg:.3f} | Trade: {trade_avg:.3f} | Order: {order_avg:.3f}")
    else:
        print(f"No latency files parsed for p = {p}")

# Optional: Plotting


df = pd.read_csv(csv_file)
plt.plot(df["p_value"], df["lookup_latency"], label="Lookup")
plt.plot(df["p_value"], df["trade_latency"], label="Trade")
plt.plot(df["p_value"], df["order_latency"], label="Order")
plt.xlabel("p value")
plt.ylabel("Average latency (s)")
plt.title("Latency vs p value")
plt.legend()
plt.grid(True)
plt.savefig("latency_plot.png")
plt.show()
