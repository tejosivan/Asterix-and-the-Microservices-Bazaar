"""
AI: ChatGPT 4o -
 Prompt: Create A script to analyze the cache impact
"""

import json
import os
import matplotlib.pyplot as plt
import numpy as np


def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)


def analyze_cache_impact():
    p_values = [0, 0.2, 0.4, 0.6, 0.8]
    cache_enabled_lookup = []
    cache_disabled_lookup = []
    cache_enabled_trade = []
    cache_disabled_trade = []
    cache_enabled_validation = []
    cache_disabled_validation = []

    for p in p_values:
        # Load cache enabled results
        enabled_file = f"results/cache_enabled_p{p}.json"
        if os.path.exists(enabled_file):
            enabled_data = load_json_file(enabled_file)
            cache_enabled_lookup.append(enabled_data["avg_lookup_latency"])
            cache_enabled_trade.append(enabled_data["avg_trade_latency"])
            cache_enabled_validation.append(enabled_data["avg_validation_latency"])
        else:
            cache_enabled_lookup.append(0)
            cache_enabled_trade.append(0)
            cache_enabled_validation.append(0)
            print(f"Warning: {enabled_file} not found")

        # Load cache disabled results
        disabled_file = f"results/cache_disabled_p{p}.json"
        if os.path.exists(disabled_file):
            disabled_data = load_json_file(disabled_file)
            cache_disabled_lookup.append(disabled_data["avg_lookup_latency"])
            cache_disabled_trade.append(disabled_data["avg_trade_latency"])
            cache_disabled_validation.append(disabled_data["avg_validation_latency"])
        else:
            cache_disabled_lookup.append(0)
            cache_disabled_trade.append(0)
            cache_disabled_validation.append(0)
            print(f"Warning: {disabled_file} not found")

    # Create plot directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)

    # Plot lookup latency comparison
    plt.figure(figsize=(10, 6))
    plt.plot(p_values, cache_enabled_lookup, marker="o", label="With Cache")
    plt.plot(p_values, cache_disabled_lookup, marker="s", label="Without Cache")
    plt.xlabel("Probability of Trade (p)")
    plt.ylabel("Average Lookup Latency (seconds)")
    plt.title("Effect of Caching on Lookup Latency")
    plt.legend()
    plt.grid(True)
    plt.savefig("plots/cache_comparison_lookup.png")

    # Plot trade latency comparison
    plt.figure(figsize=(10, 6))
    plt.plot(p_values, cache_enabled_trade, marker="o", label="With Cache")
    plt.plot(p_values, cache_disabled_trade, marker="s", label="Without Cache")
    plt.xlabel("Probability of Trade (p)")
    plt.ylabel("Average Trade Latency (seconds)")
    plt.title("Effect of Caching on Trade Latency")
    plt.legend()
    plt.grid(True)
    plt.savefig("plots/cache_comparison_trade.png")

    # Plot validation latency comparison
    plt.figure(figsize=(10, 6))
    plt.plot(p_values, cache_enabled_validation, marker="o", label="With Cache")
    plt.plot(p_values, cache_disabled_validation, marker="s", label="Without Cache")
    plt.xlabel("Probability of Trade (p)")
    plt.ylabel("Average Validation Latency (seconds)")
    plt.title("Effect of Caching on Validation Latency")
    plt.legend()
    plt.grid(True)
    plt.savefig("plots/cache_comparison_validation.png")

    # Print summary table
    print("\nCache Impact Summary:")
    print("p_value | Lookup Improvement | Trade Improvement | Validation Improvement")
    print("--------|-------------------|-------------------|----------------------")
    for i, p in enumerate(p_values):
        lookup_imp = (
            (cache_disabled_lookup[i] - cache_enabled_lookup[i])
            / cache_disabled_lookup[i]
            * 100
            if cache_disabled_lookup[i] > 0
            else 0
        )
        trade_imp = (
            (cache_disabled_trade[i] - cache_enabled_trade[i])
            / cache_disabled_trade[i]
            * 100
            if cache_disabled_trade[i] > 0
            else 0
        )
        valid_imp = (
            (cache_disabled_validation[i] - cache_enabled_validation[i])
            / cache_disabled_validation[i]
            * 100
            if cache_disabled_validation[i] > 0
            else 0
        )
        print(
            f"{p:.1f}     | {lookup_imp:.2f}%            | {trade_imp:.2f}%            | {valid_imp:.2f}%"
        )

    print("\nPlots saved to plots/cache_comparison_*.png")


def analyze_fault_tolerance():
    print("\nAnalyzing Fault Tolerance")

    # Load results
    files = ["before_failure.json", "during_failure.json", "after_recovery.json"]
    latencies = {"lookup": [], "trade": [], "validation": []}

    for file in files:
        path = f"results/{file}"
        if os.path.exists(path):
            data = load_json_file(path)
            latencies["lookup"].append(data["avg_lookup_latency"])
            latencies["trade"].append(data["avg_trade_latency"])
            latencies["validation"].append(data["avg_validation_latency"])
        else:
            latencies["lookup"].append(0)
            latencies["trade"].append(0)
            latencies["validation"].append(0)
            print(f"Warning: {path} not found")

    # Create plot directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)

    # Plot fault tolerance results
    phases = ["Before Failure", "During Failure", "After Recovery"]
    x = np.arange(len(phases))
    width = 0.25

    plt.figure(figsize=(12, 7))
    plt.bar(x - width, latencies["lookup"], width, label="Lookup")
    plt.bar(x, latencies["trade"], width, label="Trade")
    plt.bar(x + width, latencies["validation"], width, label="Validation")

    plt.xlabel("Failure Phase")
    plt.ylabel("Average Latency (seconds)")
    plt.title("Impact of Leader Failure on Latency")
    plt.xticks(x, phases)
    plt.legend()
    plt.grid(True, axis="y")
    plt.savefig("plots/fault_tolerance.png")

    # Print summary table
    print("\nFault Tolerance Summary:")
    print("Operation | Before Failure | During Failure | After Recovery")
    print("----------|----------------|----------------|---------------")
    for op in ["lookup", "trade", "validation"]:
        print(
            f"{op.capitalize()} | {latencies[op][0]:.4f}s | {latencies[op][1]:.4f}s | {latencies[op][2]:.4f}s"
        )

    print("\nPlot saved to plots/fault_tolerance.png")


def main():
    print("=== Stock Bazaar Performance Analysis ===")

    # Check if results directory exists
    if not os.path.exists("results"):
        print("Error: results directory not found!")
        return

    analyze_cache_impact()
    analyze_fault_tolerance()


if __name__ == "__main__":
    main()

    """
     End AI-assisted code piece
     """
