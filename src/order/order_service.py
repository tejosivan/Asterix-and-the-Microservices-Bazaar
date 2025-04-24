import socket
import threading
import json
import csv
import os
import time

# Basic variables initialization
next_transaction = 0
scribble_lock = threading.Lock()
order_file = "data/orders.csv"
server_port = 7777

# Use environment variable to set catalog host/port
catalog_host = os.environ.get("CATALOG_HOST", "localhost")
catalog_port = int(os.environ.get("CATALOG_PORT", "6666"))


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
    return {"status": "success", "data": {"transaction_number": transaction_num}}


"""
End AI-assisted code piece
"""


def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            request = json.loads(
                data.decode("utf-8")
            )  # Resource: https://docs.python.org/3/library/json.html
            response = {}
            if request["action"] == "trade":
                response = process_trade(
                    request["stock_name"], request["quantity"], request["order_type"]
                )
            client_socket.sendall(json.dumps(response).encode("utf-8"))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


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
    start_serve()
