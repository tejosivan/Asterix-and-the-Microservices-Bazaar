"""
AI: ChatGPT 4o
Prompt:
Now help me implement this in Paxos, with a script for testing everything
"""

import requests
import time
import random
import subprocess
import os
import sys
import signal
import csv

STOCK_LIST = ["GameStart", "BoarCo", "RottenFishCo", "MenhirCo", "CaesarTech"]
FRONTEND_HOST = "localhost"
FRONTEND_PORT = "5555"
BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"


def kill_existing_processes():
    print("Killing any existing catalog, frontend and order processes...")
    try:
        subprocess.run(["pkill", "-f", "python.*catalog.py"], capture_output=True)

        subprocess.run(["pkill", "-f", "python.*frontend.py"], capture_output=True)

        subprocess.run(["pkill", "-f", "python.*paxos_order.py"], capture_output=True)
        subprocess.run(["pkill", "-f", "python.*order.py"], capture_output=True)

        time.sleep(2)
    except Exception as e:
        print(f"Error killing existing processes: {e}")


def setup_orders_json():
    print("Setting up orders.json file...")

    try:
        orders_content = """[
        {"id": 0, "host": "localhost", "port": 7777},
        {"id": 1, "host": "localhost", "port": 7778},
        {"id": 2, "host": "localhost", "port": 7779}
    ]"""

        with open("orders.json", "w") as f:
            f.write(orders_content)

        os.makedirs("../src/frontend", exist_ok=True)
        with open("../src/frontend/orders.json", "w") as f:
            f.write(orders_content)

        os.makedirs("../src/order", exist_ok=True)
        with open("../src/order/orders.json", "w") as f:
            f.write(orders_content)

        print("orders.json files created successfully")
    except Exception as e:
        print(f"Error setting up orders.json: {e}")


def start_replicas():
    processes = []

    print("Starting catalog service...")
    catalog_log = open("catalog.log", "w")
    catalog_proc = subprocess.Popen(
        ["python", "../src/catalog/catalog.py"],
        stdout=catalog_log,
        stderr=subprocess.STDOUT,
    )
    processes.append((catalog_proc, catalog_log))
    time.sleep(2)

    print("Starting frontend service...")
    frontend_log = open("frontend.log", "w")
    frontend_proc = subprocess.Popen(
        ["python", "../src/frontend/frontend.py"],
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
    )
    processes.append((frontend_proc, frontend_log))
    time.sleep(2)

    print("Starting order service replicas...")
    for replica_id in range(3):
        log_file = open(f"order_replica_{replica_id}.log", "w")
        proc = subprocess.Popen(
            ["python", "paxos_order.py", str(replica_id)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        processes.append((proc, log_file))
        print(f"Started replica {replica_id} (PID: {proc.pid})")
        time.sleep(1)

    return processes


def stop_processes(processes):
    print("Stopping all processes...")
    for proc, log_file in processes:
        try:
            proc.terminate()
            log_file.close()
        except:
            pass


def run_concurrent_trades(num_trades=5):
    print(f"Running {num_trades} concurrent trades...")

    successful_trades = 0
    failed_trades = 0
    transaction_numbers = []

    for i in range(num_trades):
        stock_name = random.choice(STOCK_LIST)

        try:
            lookup_response = requests.get(f"{BASE_URL}/stocks/{stock_name}")
            if lookup_response.status_code != 200:
                print(f"Error looking up {stock_name}: {lookup_response.text}")
                failed_trades += 1
                continue

            time.sleep(0.5)

            request_data = {"name": stock_name, "quantity": 1, "type": "sell"}
            trade_response = requests.post(f"{BASE_URL}/orders", json=request_data)

            if trade_response.status_code == 200:
                resp = trade_response.json()
                transaction_number = resp["data"]["transaction_number"]
                transaction_numbers.append(transaction_number)
                successful_trades += 1
            else:
                print(f"Trade failed: {trade_response.text}")
                failed_trades += 1
        except Exception as e:
            print(f"Error during trade: {e}")
            failed_trades += 1

    print(f"Trades completed: {successful_trades} successful, {failed_trades} failed")
    return transaction_numbers


def check_database_consistency():
    print("Checking replica database files directly...")

    os.makedirs("data", exist_ok=True)

    replica_data = {}
    for replica_id in range(3):
        db_file = f"data/orders{replica_id}.csv"
        if os.path.exists(db_file):
            transactions = []
            with open(db_file, "r") as f:
                reader = csv.reader(f)
                try:
                    next(reader)
                    for row in reader:
                        if len(row) >= 4:
                            transactions.append(
                                {
                                    "transaction_number": row[0],
                                    "stock_name": row[1],
                                    "order_type": row[2],
                                    "quantity": row[3],
                                }
                            )
                except Exception as e:
                    print(f"Error reading file {db_file}: {e}")

            replica_data[replica_id] = transactions

            print(f"Sample transactions from replica {replica_id}:")
            for i, txn in enumerate(transactions[:5]):
                print(
                    f"  {txn['transaction_number']}: {txn['stock_name']} ({txn['order_type']}, {txn['quantity']})"
                )
            if len(transactions) > 5:
                print(f"  ... and {len(transactions) - 5} more transactions")

    if len(replica_data) < 2:
        print("Not enough replica databases to compare")
        return

    consistent = True
    reference_id = list(replica_data.keys())[0]
    reference_txns = {t["transaction_number"]: t for t in replica_data[reference_id]}

    print(f"\nComparing all replicas against replica {reference_id}...")

    for replica_id, transactions in replica_data.items():
        if replica_id == reference_id:
            continue

        replica_txns = {t["transaction_number"]: t for t in transactions}

        print(f"Comparing replica {replica_id}...")

        missing_txns = []
        for txn_num in reference_txns:
            if txn_num not in replica_txns:
                missing_txns.append(txn_num)
                consistent = False
            elif reference_txns[txn_num] != replica_txns[txn_num]:
                print(
                    f"Transaction {txn_num} differs between replicas {reference_id} and {replica_id}"
                )
                print(f"  Replica {reference_id}: {reference_txns[txn_num]}")
                print(f"  Replica {replica_id}: {replica_txns[txn_num]}")
                consistent = False

        if missing_txns:
            print(
                f"Replica {replica_id} is missing {len(missing_txns)} transactions: {missing_txns[:5]}..."
            )

        extra_txns = []
        for txn_num in replica_txns:
            if txn_num not in reference_txns:
                extra_txns.append(txn_num)
                consistent = False

        if extra_txns:
            print(
                f"Replica {replica_id} has {len(extra_txns)} extra transactions: {extra_txns[:5]}..."
            )

    if consistent:
        print("\n All replicas have identical transaction records")
        print("Paxos consensus is working correctly to maintain consistency")
    else:
        print("\n Inconsistencies detected between replicas")


def main():
    processes = None
    try:
        kill_existing_processes()
        setup_orders_json()

        processes = start_replicas()

        print("Waiting for services to initialize...")
        time.sleep(10)

        print("\nTest: Paxos Consensus with All Replicas ===")
        txn_numbers = run_concurrent_trades(5)

        print("Waiting for transactions to be processed by all replicas...")
        time.sleep(5)

        print("\nVerify Database Consistency ===")
        check_database_consistency()

    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        if processes:
            stop_processes(processes)
        print("Test completed.")


if __name__ == "__main__":
    main()

"""
End AI-assisted code piece
"""
