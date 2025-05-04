import socket
import threading
import json
import csv
import os
import time
import sys

# Basic variables initialization
next_transaction = 0
scribble_lock = threading.Lock()


# Use environment variable to set catalog host/port
catalog_host = os.environ.get("CATALOG_HOST", "localhost")
catalog_port = int(os.environ.get("CATALOG_PORT", "6666"))
replica_no = 0
order_file = "data/orders0.csv"
server_port = 7777


def setup_replicas():
    global replica_no, order_file, server_port
    if len(sys.argv) > 1:
        replica_no = int(sys.argv[1])
    else:
        replica_no = 0
    order_file = f"data/orders{replica_no}.csv"
    server_port = 7777 + replica_no


"""
AI: ChatGPT 4o  
Prompt:  
Now help me implement a Python HTTP server for processing stock orders.  
1. It should define an OrderHandler class extending BaseHTTPRequestHandler  
2. The do_POST method should only respond to /orders  

"""


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


def process_trade(stock_name, quantity, order_type):
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
        next_transaction += 1
        save_order(transaction_num, stock_name, order_type, quantity)

    # Propagate to followers
    propagate_to_followers(transaction_num, stock_name, order_type, quantity)

    return {"status": "success", "data": {"transaction_number": transaction_num}}


"""
End AI-assisted code piece
"""


"""
AI: ChatGPT 4o - used in Lab 2
 Prompt: I need help to work on Replica Synchronization Implementation
"""


def handle_client(client_socket):
    global next_transaction

    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            request = json.loads(data.decode("utf-8"))
            response = {}
            if request["action"] == "ping":
                response = {"status": "success"}
                print("debug: ping recvd")
            elif request["action"] == "trade":
                response = process_trade(
                    request["stock_name"], request["quantity"], request["order_type"]
                )
            elif request["action"] == "lookup":
                response = get_order(request["order_number"])
            elif request["action"] == "get_newer_orders":
                response = get_newer_orders(request["last_transaction"])
            elif request["action"] == "sync_order":
                response = sync_order(
                    request["transaction_number"],
                    request["stock_name"],
                    request["order_type"],
                    request["quantity"],
                )
            client_socket.sendall(json.dumps(response).encode("utf-8"))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def get_newer_orders(last_transaction):
    global next_transaction

    newer_orders = []

    if os.path.exists(order_file):
        try:
            with open(order_file, "r") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 4 and row[0].isdigit():
                        transaction_num = int(row[0])
                        if transaction_num > last_transaction:
                            newer_orders.append(
                                {
                                    "transaction_number": transaction_num,
                                    "stock_name": row[1],
                                    "order_type": row[2],
                                    "quantity": int(row[3]),
                                }
                            )
        except Exception as e:
            print(f"Error reading orders for sync: {e}")
            return {"status": "error", "error": f"Failed to read orders: {str(e)}"}

    return {"status": "success", "orders": newer_orders}


def sync_order(transaction_num, stock_name, order_type, quantity):
    global next_transaction

    with scribble_lock:
        # Make sure we haven't already recorded this transaction
        if transaction_num >= next_transaction:
            next_transaction = transaction_num + 1
            save_order(transaction_num, stock_name, order_type, quantity)
            return {"status": "success"}
        else:
            return {"status": "already_processed"}


def sync_with_replicas():
    global next_transaction
    last_transaction = -1

    # Find the last transaction we have
    if os.path.exists(order_file):
        try:
            with open(order_file, "r") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    if row and len(row) > 0:
                        try:
                            transaction_num = int(row[0])
                            last_transaction = max(last_transaction, transaction_num)
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Error reading order log for sync: {e}")

    # Get all replicas
    orders_json_path = "orders.json"
    if not os.path.exists(orders_json_path):
        orders_json_path = "../frontend/orders.json"

    try:
        with open(orders_json_path, "r") as f:
            replicas = json.load(f)
    except FileNotFoundError:
        print(f"Warning: Could not find orders.json")
        return

    for replica in replicas:
        # Skip current replica
        if replica["port"] == server_port:
            continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((replica["host"], replica["port"]))
                request = {
                    "action": "get_newer_orders",
                    "last_transaction": last_transaction,
                }
                sock.sendall(json.dumps(request).encode("utf-8"))

                response = sock.recv(4096)
                response_data = json.loads(response.decode("utf-8"))

                if response_data["status"] == "success" and "orders" in response_data:
                    for order in response_data["orders"]:
                        with scribble_lock:
                            if order["transaction_number"] >= next_transaction:
                                next_transaction = order["transaction_number"] + 1
                            save_order(
                                order["transaction_number"],
                                order["stock_name"],
                                order["order_type"],
                                order["quantity"],
                            )
                    print(
                        f"Synced {len(response_data['orders'])} orders from replica at {replica['host']}:{replica['port']}"
                    )

                    # If we got orders, we're done - no need to check other replicas
                    if response_data["orders"]:
                        break

        except Exception as e:
            print(
                f"Failed to sync with replica at {replica['host']}:{replica['port']}: {e}"
            )


"""
End AI-assisted code piece
"""


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


def get_order(order_num):
    if not os.path.exists(order_file):
        return {"status": "error", "error": {"code": 404, "message": "Order not found"}}
    file = open(order_file, "r", newline="")
    reader = csv.reader(file)
    next(reader)  # Skip header
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

    file.close()
    return {
        "status": "error",
        "error": {"code": 404, "message": "Order not found"},
    }


def propagate_to_followers(transaction_num, stock_name, order_type, quantity):
    # Read replicas configuration
    try:
        orders_json_path = "orders.json"
        if not os.path.exists(orders_json_path):
            orders_json_path = "../frontend/orders.json"

        with open(orders_json_path, "r") as f:
            replicas = json.load(f)
    except Exception as e:
        print(f"Failed to read replicas: {e}")
        return

    for replica in replicas:
        # Skip current replica
        if replica["port"] == server_port:
            continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect((replica["host"], replica["port"]))
                request = {
                    "action": "sync_order",
                    "transaction_number": transaction_num,
                    "stock_name": stock_name,
                    "order_type": order_type,
                    "quantity": quantity,
                }
                sock.sendall(json.dumps(request).encode("utf-8"))
                # We don't need to wait for a response here
        except Exception as e:
            print(
                f"Failed to propagate order to replica at {replica['host']}:{replica['port']}: {e}"
            )


def start_serve():
    init_txn_ctr()
    sync_with_replicas()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host = "0.0.0.0"
    server.bind((host, server_port))
    server.listen(10)
    print(f"Order service running on {host}:{server_port}")
    try:
        while True:
            client_sock, address = server.accept()
            print(f"New connection from {address}")
            client_thread = threading.Thread(target=handle_client, args=(client_sock,))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down the order service...")
    finally:
        server.close()


if __name__ == "__main__":
    setup_replicas()
    start_serve()
