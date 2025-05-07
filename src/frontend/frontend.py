from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlparse
import socket
import threading
import os
from collections import OrderedDict
import sys

CATALOG_HOST = os.environ.get("CATALOG_HOST", "localhost")
CATALOG_PORT = int(os.environ.get("CATALOG_PORT", "6666"))
ORDER_HOST = os.environ.get("ORDER_HOST", "localhost")
ORDER_PORT = int(os.environ.get("ORDER_PORT", "7777"))
PORT = int(os.environ.get("PORT", "5555"))

local_data = threading.local()

ORDER_REPLICAS = []
leader = None


def get_replica_details():
    global ORDER_REPLICAS
    with open("orders.json", "r") as f:
        ORDER_REPLICAS = json.load(f)
    ORDER_REPLICAS.sort(key=lambda i: i["id"])


# AI: ChatGPT4o
# prompt: Help me with some starter code to go through replicas from a list of replicas and to "ping" them to see if they're up


def leader_selection():
    global leader
    leader = None

    for replica in ORDER_REPLICAS:
        try:
            print(
                f"Trying to connect to replica {replica['id']} at {replica['host']}:{replica['port']}"
            )  # add this
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((replica["host"], replica["port"]))

            ping_request = {"action": "ping"}
            sock.sendall(json.dumps(ping_request).encode("utf-8"))
            response = sock.recv(4096)
            reply = json.loads(response.decode("utf-8"))
            sock.close()

            if reply.get("status") == "success":
                leader = replica
                print(f"Leader selected: Replica {replica['id']}")
                return
        except Exception as e:
            print(f"Could not reach Replica {replica['id']}")

    print("No leader found!")


# end prompt: Help me with some starter code to go through replicas from a list of replicas and to "ping" them to see if they're up


# AI: ChatGPT4o
# prompt: i need to implement an LRU cache in python. Give me some starter code
class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


# end AI: prompt: i need to implement an LRU cache in python. Give me some starter code
cache = LRUCache(7)  # change


# AI: ChatGPT4o
# prompt: my cache doesnt get updated upon a trade. Give me some starter code for my catalog service to invalidate cache entries that have been updated. i want it in basic python and sockets, not flask.
INVALIDATION_PORT = 5556


def invalidation_listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", INVALIDATION_PORT))
    server.listen(5)
    print(f"Invalidation listener running on port {INVALIDATION_PORT}")

    while True:
        client_socket, addr = server.accept()
        data = client_socket.recv(1024)
        try:
            message = json.loads(data.decode("utf-8"))
            stock = message.get("invalidate")
            if stock and stock in cache.cache:
                del cache.cache[stock]
                print(f"Cache invalidated via server push: {stock}")
        except Exception as e:
            print(f"Error in invalidation listener: {e}")
        client_socket.close()


# end prompt: my cache doesnt get updated upon a trade. Give me some starter code for my catalog service to invalidate cache entries that have been updated. i want it in basic python and sockets, not flask.


"""
AI: ChatGPT 4o - used in Lab 2
 Prompt: I need help implementing socket connection management for a microservices application. Can you help me write functions that:

Create and maintain persistent socket connections to backend services
Include proper error handling with reconnection logic
Use thread-local storage to ensure thread safety
Handle sending JSON requests and receiving JSON responses
"""


def get_catalog_socket():
    if not hasattr(local_data, "catalog_socket"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((CATALOG_HOST, CATALOG_PORT))
        local_data.catalog_socket = sock
    return local_data.catalog_socket


def get_order_socket():
    if not hasattr(local_data, "order_socket"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ORDER_HOST, ORDER_PORT))
        local_data.order_socket = sock
    return local_data.order_socket


def ask_catalog(request):
    try:
        sock = get_catalog_socket()
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        return json.loads(response.decode("utf-8"))
    except Exception as e:
        print(f"Error talking to catalog: {e}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((CATALOG_HOST, CATALOG_PORT))
            local_data.catalog_socket = sock
            sock.sendall(json.dumps(request).encode("utf-8"))
            response = sock.recv(4096)
            return json.loads(response.decode("utf-8"))
        except Exception as e2:
            print(f"Reconnection failed: {e2}")
            return {
                "status": "error",
                "error": {"code": 500, "message": "Catalog service unavailable"},
            }


def ask_order(request):
    global leader
    max_retries = 3
    retries = 0

    while retries < max_retries:
        if leader is None:
            leader_selection()
            if leader is None:
                return {
                    "status": "error",
                    "error": {"code": 503, "message": "No leader found"},
                }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # We are setting a timeout value here
                sock.connect((leader["host"], leader["port"]))
                sock.sendall(json.dumps(request).encode("utf-8"))
                response = sock.recv(4096)
                return json.loads(response.decode("utf-8"))

        except Exception as e:
            print(f"Error talking to leader: {e}")
            retries += 1
            leader = None

    return {
        "status": "error",
        "error": {
            "code": 503,
            "message": "Order service unavailable after multiple retries",
        },
    }


class StockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path).path

        if parsed_path.startswith("/stocks/"):
            stock_name = parsed_path[8:]
            print(f"Looking up stock: {stock_name}")

            # LRU Cache bit
            stock_details = None
            if CACHE_FLAG:
                print(f"Cache enabled")
                stock_details = cache.get(stock_name)
            else:
                print(f"Cache disabled")
                stock_details = -1

            if stock_details == -1:
                print(f" Cache miss, contacting catalog")
                catalog_request = {"action": "lookup", "stock_name": stock_name}
                service_response = ask_catalog(catalog_request)
                if service_response["status"] == "success":
                    stock_details = service_response["data"]
                    if CACHE_FLAG:
                        cache.put(stock_name, stock_details)
                    response = {"data": stock_details}
                    self.send_response(200)
                else:
                    response = {"error": service_response["error"]}
                    self.send_response(service_response["error"]["code"])

            else:
                print(f"Cache hit!")
                response = {"data": stock_details}
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif parsed_path.startswith("/orders/"):
            order_num = parsed_path[8:]
            if order_num.isdigit():
                order_num = int(order_num)
                print(f"Looking up order: {order_num}")
                order_request = {"action": "lookup", "order_number": order_num}
                service_response = ask_order(order_request)
                if service_response["status"] == "success":
                    response = {"data": service_response["data"]}
                    self.send_response(200)
                else:
                    response = {"error": service_response["error"]}
                    self.send_response(service_response["error"]["code"])
            else:
                response = {"error": {"code": 400, "message": "Invalid order number"}}
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        else:
            self.send_error(404, "Invalid endpoint")

    """
     End AI-assisted code piece
     """

    def do_POST(self):
        parsed_path = urlparse(self.path).path
        if parsed_path == "/orders":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                stock_name = data.get("name")
                quantity = data.get("quantity")
                order_type = data.get("type")
                print(f"Processing order: {order_type} {quantity} of {stock_name}")
                order_request = {
                    "action": "trade",
                    "stock_name": stock_name,
                    "quantity": quantity,
                    "order_type": order_type,
                }
                service_response = ask_order(order_request)
                if service_response["status"] == "success":
                    response = {"data": service_response["data"]}
                    self.send_response(200)
                else:
                    response = {"error": service_response["error"]}
                    self.send_response(service_response["error"]["code"])
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except json.JSONDecodeError:
                response = {"error": {"code": 400, "message": "Invalid JSON format"}}
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_error(404, "Invalid endpoint")


# official docs and https://pymotw.com/2/BaseHTTPServer/
def serve():
    host = "0.0.0.0"
    port = PORT
    threading.Thread(target=invalidation_listener, daemon=True).start()
    server = ThreadingHTTPServer((host, port), StockHandler)
    print(f"Frontend server running on port {port}")
    server.serve_forever()

CACHE_FLAG = True # we can pass a commandline argument to set to false: python frontend.py --cache=False
if __name__ == "__main__":
    for arg in sys.argv:
        if arg.lower() == "--cache=false":
            CACHE_FLAG = False
    get_replica_details()
    leader_selection()
    serve()
