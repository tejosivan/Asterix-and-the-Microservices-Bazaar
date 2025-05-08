import socket
import threading
import json
import csv
import os

# Variables Initialization
stock_check = {} # dictionary format: {name: {price, quantity}}
guardian = threading.RLock()
catalog_port = 6666

stock_file = "data/catalog.csv"


# Main Function
def load_stocks():  # labask - 10 different stocks, 100 volume
    global stock_check
    if not os.path.exists(stock_file):
        stock_check = {
            "GameStart": {"price": 15.99, "quantity": 100},
            "RottenFishCo": {"price": 2.50, "quantity": 100},
            "BoarCo": {"price": 7.11, "quantity": 100},
            "MenhirCo": {"price": 20.00, "quantity": 100},
            "CaesarTech": {"price": 1.00, "quantity": 100},
            "Reneium": {"price": 14.99, "quantity": 100},
            "Goscinnyium": {"price": 22.50, "quantity": 100},
            "PiloteCo": {"price": 17.11, "quantity": 100},
            "DogmatixCo": {"price": 20.00, "quantity": 100},
            "LutetiaTech": {"price": 11.00, "quantity": 100},
        }
        save_stocks()
    else:
        stock_check = {}
        try:
            with open(stock_file, "r") as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if len(row) >= 3:
                        name, price, quantity = row[0], float(row[1]), int(row[2])
                        stock_check[name] = {"price": price, "quantity": quantity}
        except Exception as e:
            print(f"Reading failed: {e}")
            stock_check = {
                "GameStart": {"price": 15.99, "quantity": 100},
                "RottenFishCo": {"price": 2.50, "quantity": 50},
                "BoarCo": {"price": 7.11, "quantity": 382},
                "MenhirCo": {"price": 20.00, "quantity": 25},
            }
    print("Stock catalog loaded:", stock_check)


def save_stocks(): # to store details in csv file
    try:
        if not os.path.exists("data"):
            os.makedirs("data")
        with open(stock_file, "w", newline="") as file:
            writer = csv.writer(
                file
            )  # Resource: https://docs.python.org/3/library/csv.html
            writer.writerow(["name", "price", "quantity"])
            for name, details in stock_check.items():
                writer.writerow([name, details["price"], details["quantity"]])
    except Exception as e:
        print(f"Failed to write stocks: {e}")


def find_stock(stock_name): #looking up stock details
    with guardian:
        if stock_name in stock_check:
            return {
                "status": "success",
                "data": {
                    "name": stock_name,
                    "price": stock_check[stock_name]["price"],
                    "quantity": stock_check[stock_name]["quantity"],
                },
            }
        else:
            return {
                "status": "error",
                "error": {"code": 404, "message": "stock not found"},
            }


def change_quantity(stock_name, qty_change): # to update stock volume
    with guardian:
        if stock_name not in stock_check:
            return {
                "status": "error",
                "error": {"code": 404, "message": "stock not found"},
            }
        current_qty = stock_check[stock_name]["quantity"]
        new_qty = current_qty + qty_change
        if new_qty < 0:
            return {
                "status": "error",
                "error": {"code": 400, "message": "insufficient quantity"},
            }
        stock_check[stock_name]["quantity"] = new_qty
        save_stocks()
        send_invalidation(stock_name)  #calling invalidate function
        return {
            "status": "success",
            "data": {
                "name": stock_name,
                "price": stock_check[stock_name]["price"],
                "quantity": new_qty,
            },
        }


def handle_client(client_socket): # to deal with JSON requests from clients
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            request = json.loads(data.decode("utf-8"))
            response = {}
            if request["action"] == "lookup":
                response = find_stock(request["stock_name"])
            elif request["action"] == "update":
                response = change_quantity(
                    request["stock_name"], request["quantity_change"]
                )
            client_socket.sendall(json.dumps(response).encode("utf-8"))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


# AI: ChatGPT4o
# prompt: my cache doesnt get updated upon a trade. Give me some starter code for my catalog service to invalidate cache entries that have been updated. i want it in basic python and sockets, not flask.
def send_invalidation(stock_name):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 5556))
            message = json.dumps({"invalidate": stock_name})
            sock.sendall(message.encode("utf-8"))
    except Exception as e:
        print(f"Invalidation send failed: {e}")


# end prompt: my cache doesnt get updated upon a trade. Give me some starter code for my catalog service to invalidate cache entries that have been updated. i want it in basic python and sockets, not flask.


# driver code
def start_server():
    load_stocks()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host = "0.0.0.0"
    server.bind((host, catalog_port))
    server.listen(10) # # of connections 
    print(f"Catalog service running on {host}:{catalog_port}")
    try:
        while True:
            client_sock, address = server.accept()
            print(f"New connection from {address}")
            client_thread = threading.Thread(target=handle_client, args=(client_sock,))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down the catalog service...")
    finally:
        server.close()


# invoke driver code start
if __name__ == "__main__":
    start_server()