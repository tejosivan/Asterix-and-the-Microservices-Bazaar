from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlparse
import socket
import threading
import os

CATALOG_HOST = os.environ.get("CATALOG_HOST", "localhost")
CATALOG_PORT = int(os.environ.get("CATALOG_PORT", "6666"))
ORDER_HOST = os.environ.get("ORDER_HOST", "localhost")
ORDER_PORT = int(os.environ.get("ORDER_PORT", "7777"))
PORT = int(os.environ.get("PORT", "5555"))

local_data = threading.local()


# https://pymotw.com/2/BaseHTTPServer/
# also AI
"""
AI: ChatGPT 4o 
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
    try:
        sock = get_order_socket()
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        return json.loads(response.decode("utf-8"))
    except Exception as e:
        print(f"Error talking to order service: {e}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ORDER_HOST, ORDER_PORT))
            local_data.order_socket = sock
            sock.sendall(json.dumps(request).encode("utf-8"))
            response = sock.recv(4096)
            return json.loads(response.decode("utf-8"))
        except Exception as e2:
            print(f"Reconnection failed: {e2}")
            return {
                "status": "error",
                "error": {"code": 500, "message": "Order service unavailable"},
            }


class StockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path).path
        if parsed_path.startswith("/stocks/"):
            stock_name = parsed_path[8:]
            print(f"Looking up stock: {stock_name}")
            catalog_request = {"action": "lookup", "stock_name": stock_name}
            service_response = ask_catalog(catalog_request)
            if service_response["status"] == "success":
                response = {"data": service_response["data"]}
                self.send_response(200)
            else:
                response = {"error": service_response["error"]}
                self.send_response(service_response["error"]["code"])
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
    server = ThreadingHTTPServer((host, port), StockHandler)
    print(f"Frontend server running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
