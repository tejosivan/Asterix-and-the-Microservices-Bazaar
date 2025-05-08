"""
AI: ChatGPT 4o
Prompt:
Implement a fault-tolerant distributed order processing system using the Paxos consensus algorithm where:

Multiple replicas must coordinate to agree on transaction ordering
The system should handle network partitions gracefully
Leader election should occur automatically when the current leader fails
Include mechanisms for log replication and state recovery
Include both the algorithm pseudocode and a working Python implementation.
"""

import socket
import threading
import json
import csv
import os
import time
import sys
import random


next_transaction = 0
scribble_lock = threading.Lock()


proposal_number = 0
accepted_proposals = {}
highest_accepted_proposal = -1
promised_proposal = -1
learned_values = {}


catalog_host = os.environ.get("CATALOG_HOST", "localhost")
catalog_port = int(os.environ.get("CATALOG_PORT", "6666"))
replica_no = 0
order_file = "data/orders0.csv"
server_port = 7777


replicas = [
    {"id": 0, "host": "localhost", "port": 7777},
    {"id": 1, "host": "localhost", "port": 7778},
    {"id": 2, "host": "localhost", "port": 7779},
]


def setup_replicas():
    global replica_no, order_file, server_port
    if len(sys.argv) > 1:
        replica_no = int(sys.argv[1])
    else:
        replica_no = 0

    os.makedirs("data", exist_ok=True)

    order_file = f"data/orders{replica_no}.csv"
    server_port = 7777 + replica_no


def save_order(transaction_num, stock_name, order_type, quantity):
    try:
        if not os.path.exists("data"):
            os.makedirs("data")
        file_exists = os.path.exists(order_file)
        with open(order_file, "a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(
                    [
                        "transaction_number",
                        "stock_name",
                        "order_type",
                        "quantity",
                        "timestamp",
                    ]
                )
            writer.writerow(
                [transaction_num, stock_name, order_type, quantity, time.time()]
            )
    except Exception as e:
        print(f"Failed to log order: {e}")


def ask_catalog(request):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((catalog_host, catalog_port))
            sock.sendall(json.dumps(request).encode("utf-8"))
            response = sock.recv(4096)
            return json.loads(response.decode("utf-8"))
    except Exception as e:
        print(f"Failed to talk to catalog: {e}")
        return {
            "status": "error",
            "error": {
                "code": 500,
                "message": f"catalog service communication error: {str(e)}",
            },
        }


def generate_proposal_number():
    global proposal_number
    with scribble_lock:
        proposal_number += 1
        return (proposal_number * 10) + replica_no


def send_message_to_replica(replica, message):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect((replica["host"], replica["port"]))
            sock.sendall(json.dumps(message).encode("utf-8"))
            response = sock.recv(4096)
            return json.loads(response.decode("utf-8"))
    except Exception as e:
        return None


def phase1a_prepare(value):
    global highest_accepted_proposal
    prop_num = generate_proposal_number()

    promises = 0
    highest_accepted = None
    highest_accepted_num = -1

    reachable_replicas = 0

    for replica in replicas:
        message = {"action": "paxos_prepare", "proposal_number": prop_num}

        response = None
        if replica["id"] == replica_no:
            response = handle_prepare(message)
            reachable_replicas += 1
        else:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    sock.connect((replica["host"], replica["port"]))
                    sock.sendall(json.dumps(message).encode("utf-8"))
                    data = sock.recv(4096)
                    response = json.loads(data.decode("utf-8"))
                    reachable_replicas += 1
            except Exception as e:
                print(f"Failed to contact replica {replica['id']}: {e}")

        if response and response.get("status") == "promise":
            promises += 1
            if response.get("accepted_proposal", -1) > highest_accepted_num:
                highest_accepted_num = response.get("accepted_proposal", -1)
                highest_accepted = response.get("accepted_value")

    if reachable_replicas == 0:
        return None, None

    majority = (reachable_replicas // 2) + 1

    if promises >= majority:
        print(f"Received majority of promises ({promises}/{reachable_replicas})")
        return prop_num, highest_accepted if highest_accepted is not None else value
    else:
        print(f"Failed to get majority of promises ({promises}/{reachable_replicas})")
        return None, None


def phase2a_accept(proposal_num, value):
    accepts = 0
    reachable_replicas = 0

    for replica in replicas:
        message = {
            "action": "paxos_accept",
            "proposal_number": proposal_num,
            "value": value,
        }

        response = None
        if replica["id"] == replica_no:
            response = handle_accept(message)
            reachable_replicas += 1
        else:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    sock.connect((replica["host"], replica["port"]))
                    sock.sendall(json.dumps(message).encode("utf-8"))
                    data = sock.recv(4096)
                    response = json.loads(data.decode("utf-8"))
                    reachable_replicas += 1
            except Exception as e:
                print(f"Failed to contact replica {replica['id']}: {e}")

        if response and response.get("status") == "accepted":
            accepts += 1

    if reachable_replicas == 0:
        print("No replicas reachable")
        return False

    majority = (reachable_replicas // 2) + 1
    print(f"Reachable replicas: {reachable_replicas}, Majority needed: {majority}")

    if accepts >= majority:
        print(
            f"Proposal {proposal_num} accepted by majority ({accepts}/{reachable_replicas})"
        )
        return True
    else:
        print(
            f"Proposal {proposal_num} not accepted by majority ({accepts}/{reachable_replicas})"
        )
        return False


def phase3_learn(proposal_num, value):
    print(f"Sending learn message for proposal {proposal_num}")

    handle_learn(
        {"action": "paxos_learn", "proposal_number": proposal_num, "value": value}
    )

    for replica in replicas:
        if replica["id"] == replica_no:
            continue

        message = {
            "action": "paxos_learn",
            "proposal_number": proposal_num,
            "value": value,
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.connect((replica["host"], replica["port"]))
                sock.sendall(json.dumps(message).encode("utf-8"))
        except Exception as e:
            print(f"Failed to send learn message to replica {replica['id']}: {e}")
    return True


def handle_prepare(request):
    global promised_proposal, highest_accepted_proposal, accepted_proposals

    prop_num = request["proposal_number"]

    with scribble_lock:
        if prop_num > promised_proposal:
            promised_proposal = prop_num

            response = {
                "status": "promise",
                "accepted_proposal": highest_accepted_proposal,
                "accepted_value": accepted_proposals.get(highest_accepted_proposal),
            }
            return response
        else:
            return {"status": "rejected", "reason": "already promised higher proposal"}


def handle_accept(request):
    global promised_proposal, highest_accepted_proposal, accepted_proposals

    prop_num = request["proposal_number"]
    value = request["value"]

    with scribble_lock:
        if prop_num >= promised_proposal:
            promised_proposal = prop_num
            highest_accepted_proposal = prop_num
            accepted_proposals[prop_num] = value

            response = {"status": "accepted"}
            return response
        else:
            return {"status": "rejected", "reason": "already promised higher proposal"}


def handle_learn(request):
    global learned_values

    prop_num = request["proposal_number"]
    value = request["value"]

    with scribble_lock:
        learned_values[prop_num] = value

    apply_learned_value(value)

    return {"status": "learned"}


def apply_learned_value(value):
    global next_transaction

    if not value:
        return

    stock_name = value["stock_name"]
    quantity = value["quantity"]
    order_type = value["order_type"]
    transaction_num = value["transaction_number"]

    with scribble_lock:
        if transaction_num >= next_transaction:
            next_transaction = transaction_num + 1

    save_order(transaction_num, stock_name, order_type, quantity)

    print(
        f"Applied learned value: {transaction_num}, {stock_name}, {order_type}, {quantity}"
    )


def paxos_propose_value(value):
    proposal_num, final_value = phase1a_prepare(value)
    if not proposal_num:
        return False, "Failed to get majority of promises"

    if not phase2a_accept(proposal_num, final_value):
        return False, "Failed to get majority of accepts"

    phase3_learn(proposal_num, final_value)

    return True, "Value proposed and accepted"


def process_trade_with_paxos(stock_name, quantity, order_type):
    global next_transaction

    quantity_change = quantity if order_type == "sell" else -quantity
    catalog_request = {
        "action": "update",
        "stock_name": stock_name,
        "quantity_change": quantity_change,
    }
    catalog_response = ask_catalog(catalog_request)

    if catalog_response["status"] == "error":
        return catalog_response

    with scribble_lock:
        transaction_num = next_transaction

    value = {
        "transaction_number": transaction_num,
        "stock_name": stock_name,
        "order_type": order_type,
        "quantity": quantity,
    }

    success, message = paxos_propose_value(value)

    if success:
        with scribble_lock:
            next_transaction += 1
        return {"status": "success", "data": {"transaction_number": transaction_num}}
    else:
        return {"status": "error", "error": {"code": 500, "message": message}}


def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            request = json.loads(data.decode("utf-8"))
            response = {}

            if request["action"] == "ping":
                response = {"status": "success"}
            elif request["action"] == "trade":
                response = process_trade_with_paxos(
                    request["stock_name"], request["quantity"], request["order_type"]
                )
            elif request["action"] == "lookup":
                response = get_order(request["order_number"])
            elif request["action"] == "paxos_prepare":
                response = handle_prepare(request)
            elif request["action"] == "paxos_accept":
                response = handle_accept(request)
            elif request["action"] == "paxos_learn":
                response = handle_learn(request)

            client_socket.sendall(json.dumps(response).encode("utf-8"))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def get_order(order_num):
    if os.path.exists(order_file):
        try:
            with open(order_file, "r") as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if len(row) >= 4 and row[0].isdigit() and int(row[0]) == order_num:
                        return {
                            "status": "success",
                            "data": {
                                "number": int(row[0]),
                                "name": row[1],
                                "type": row[2],
                                "quantity": int(row[3]),
                            },
                        }
        except Exception as e:
            print(f"Error reading order file: {e}")

    for replica_id in range(3):
        if replica_id == replica_no:
            continue

        other_order_file = f"data/orders{replica_id}.csv"
        if os.path.exists(other_order_file):
            try:
                with open(other_order_file, "r") as file:
                    reader = csv.reader(file)
                    next(reader)
                    for row in reader:
                        if (
                            len(row) >= 4
                            and row[0].isdigit()
                            and int(row[0]) == order_num
                        ):
                            return {
                                "status": "success",
                                "data": {
                                    "number": int(row[0]),
                                    "name": row[1],
                                    "type": row[2],
                                    "quantity": int(row[3]),
                                },
                            }
            except Exception as e:
                print(f"Error reading replica {replica_id} order file: {e}")

    return {
        "status": "error",
        "error": {"code": 404, "message": "Order not found"},
    }


def init_txn_ctr():
    global next_transaction
    if os.path.exists(order_file):
        try:
            with open(order_file, "r") as file:
                reader = csv.reader(file)
                next(reader)
                max_transaction = -1
                for row in reader:
                    if row and len(row) > 0:
                        try:
                            transaction_num = int(row[0])
                            max_transaction = max(max_transaction, transaction_num)
                        except ValueError:
                            pass
                next_transaction = max_transaction + 1
        except Exception as e:
            print(f"Error reading order log: {e}")
            next_transaction = 0
    else:
        next_transaction = 0
    print(f"Transaction counter initialized to {next_transaction}")


def start_serve():
    init_txn_ctr()

    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)
        result = test_socket.connect_ex(("localhost", server_port))

        if result == 0:
            print(
                f"Port {server_port} is already in use. Trying to kill existing process..."
            )

            try:
                import subprocess

                subprocess.run(
                    ["pkill", "-f", f"python.*paxos_order.py.*{replica_no}"],
                    capture_output=True,
                )
                time.sleep(1)
            except Exception as e:
                print(f"Failed to kill existing process: {e}")

        test_socket.close()
    except Exception as e:
        print(f"Error checking port: {e}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host = "0.0.0.0"

    try:
        server.bind((host, server_port))
        server.listen(10)
        print(f"Paxos Order service running on {host}:{server_port}")

        while True:
            client_sock, address = server.accept()
            print(f"New connection from {address}")
            client_thread = threading.Thread(target=handle_client, args=(client_sock,))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down the order service...")
    except Exception as e:
        print(f"Error starting server: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    setup_replicas()
    start_serve()

"""
End AI-assisted code piece
"""
