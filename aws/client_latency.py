# AI: ChatGPT4o
# prompt: i need to implement an script to measure client latency

import sys
import requests
import random
import time
import os
import json

STOCK_LIST = [
    "GameStart",
    "BoarCo",
    "RottenFishCo",
    "MenhirCo",
    "CaesarTech",
    "Reneium",
    "Goscinnyium",
    "PiloteCo",
    "DogmatixCo",
    "LutetiaTech",
]
trades_record = []


def run_client(p, stock_name, output_file):
    print(f"\n\nEstablishing a session for {stock_name} with p={p}...")
    num_of_trades = 0

    # Replace with your EC2 public DNS
    FRONTEND_HOST = "ec2-54-146-163-93.compute-1.amazonaws.com"
    FRONTEND_PORT = "5555"
    BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

    # Track latencies
    latencies = {"lookup": [], "trade": [], "validation": []}

    with requests.Session() as session:
        for i in range(10):  # Run 10 iterations
            print(f"Iteration {i + 1}")

            # Measure lookup latency
            start_time = time.time()
            lookup_response = session.get(f"{BASE_URL}/stocks/{stock_name}")
            lookup_latency = time.time() - start_time
            latencies["lookup"].append(lookup_latency)
            print(f"Lookup latency: {lookup_latency:.4f}s")

            if lookup_response.status_code == 200:
                response = lookup_response.json()
                price = response["data"]["price"]
                quantity = response["data"]["quantity"]
                print(
                    f"{stock_name} lookup results: \n Price = {price} \n Quantity = {quantity}"
                )

                # Decide whether to trade based on probability p
                if random.random() < p and quantity > 0:
                    request_data = {"name": stock_name, "quantity": 1, "type": "sell"}

                    # Measure trade latency
                    start_time = time.time()
                    trade_response = session.post(
                        f"{BASE_URL}/orders", json=request_data
                    )
                    trade_latency = time.time() - start_time
                    latencies["trade"].append(trade_latency)
                    print(f"Trade latency: {trade_latency:.4f}s")

                    if trade_response.status_code == 200:
                        resp = trade_response.json()
                        transaction_number = resp["data"]["transaction_number"]
                        print(
                            f"One stock purchased of {stock_name}, transaction_number = {transaction_number}"
                        )
                        num_of_trades += 1
                        record = {
                            "order_number": transaction_number,
                            "stock_name": stock_name,
                            "type": "sell",
                            "quantity": 1,
                        }
                        trades_record.append(record)
                    else:
                        print(f"Trade Failed: {trade_response.text}")
                else:
                    print("No trade this iteration (based on probability or no stock)")
            else:
                print(f"Error looking up stock: {lookup_response.text}")

            time.sleep(1)  # Slight delay between iterations

        # Validation phase
        print("\nValidating transactions...")
        for trade in trades_record:
            transaction_number = trade["order_number"]

            # Measure validation latency
            start_time = time.time()
            validation_resp = session.get(f"{BASE_URL}/orders/{transaction_number}")
            validation_latency = time.time() - start_time
            latencies["validation"].append(validation_latency)
            print(
                f"Validation latency for transaction {transaction_number}: {validation_latency:.4f}s"
            )

            if validation_resp.status_code == 200:
                server_copy_trade = validation_resp.json()["data"]
                if (
                    server_copy_trade["name"] == trade["stock_name"]
                    and server_copy_trade["type"] == trade["type"]
                    and server_copy_trade["quantity"] == trade["quantity"]
                ):
                    print(f"Transaction {transaction_number} correctly verified.")
                else:
                    print(
                        f"Transaction {transaction_number} doesn't match the server's order."
                    )
            else:
                print(
                    f"Error validating transaction {transaction_number}: {validation_resp.text}"
                )

    # Calculate average latencies
    avg_lookup = (
        sum(latencies["lookup"]) / len(latencies["lookup"])
        if latencies["lookup"]
        else 0
    )
    avg_trade = (
        sum(latencies["trade"]) / len(latencies["trade"]) if latencies["trade"] else 0
    )
    avg_validation = (
        sum(latencies["validation"]) / len(latencies["validation"])
        if latencies["validation"]
        else 0
    )

    print(f"\nSummary:")
    print(f"Average lookup latency: {avg_lookup:.4f}s")
    print(f"Average trade latency: {avg_trade:.4f}s")
    print(f"Average validation latency: {avg_validation:.4f}s")
    print(f"Number of trades: {num_of_trades}")

    # Save results to file
    results = {
        "p_value": p,
        "stock_name": stock_name,
        "num_trades": num_of_trades,
        "avg_lookup_latency": avg_lookup,
        "avg_trade_latency": avg_trade,
        "avg_validation_latency": avg_validation,
        "lookup_latencies": latencies["lookup"],
        "trade_latencies": latencies["trade"],
        "validation_latencies": latencies["validation"],
    }

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 client_latency.py <probability> <output_file>")
        sys.exit(1)

    try:
        p = float(sys.argv[1])
        if not 0 <= p <= 1:
            print("P needs to be in [0,1], defaulting to 0.8")
            p = 0.8
    except ValueError:
        print("P should be a float! Defaulting to 0.8")
        p = 0.8

    output_file = sys.argv[2]

    # Pick a random stock
    stock_name = random.choice(STOCK_LIST)
    run_client(p, stock_name, output_file)

# end prompt: Received Input
