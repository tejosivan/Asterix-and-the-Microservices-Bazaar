import socket
import json
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


"""
AI: ChatGPT 4o
1. Tests basic functionality including:
   - Looking up existing stocks
   - Handling non-existent stock requests
   - Updating stock quantities
   - Validating quantity constraints
"""


def test_lookup_stock():
    print("\nTest: Looking up an existing stock")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "lookup", "stock_name": "GameStart"}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))

        print(f"Response: {result}")
        assert result["status"] == "success", "Expected success status"
        assert "data" in result, "Expected data in response"
        assert result["data"]["name"] == "GameStart", "Expected correct stock name"
        assert "price" in result["data"], "Expected price in response"
        assert "quantity" in result["data"], "Expected quantity in response"
        print("✓ Test passed: Stock lookup successful")


def test_lookup_nonexistent_stock():
    print("\nTest: Looking up a non-existent stock")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "lookup", "stock_name": "NonExistentStock"}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))

        print(f"Response: {result}")
        assert result["status"] == "error", "Expected error status"
        assert "error" in result, "Expected error in response"
        assert result["error"]["code"] == 404, "Expected 404 error code"
        print("✓ Test passed: Non-existent stock lookup returns error")


def test_update_quantity():
    print("\nTest: Updating stock quantity")

    # First get current quantity
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "lookup", "stock_name": "BoarCo"}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))
        initial_quantity = result["data"]["quantity"]

    # Update the quantity
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "update", "stock_name": "BoarCo", "quantity_change": -1}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))

        print(f"Response: {result}")
        assert result["status"] == "success", "Expected success status"
        assert "data" in result, "Expected data in response"
        assert result["data"]["quantity"] == initial_quantity - 1, (
            "Expected quantity to decrease by 1"
        )
        print("✓ Test passed: Stock quantity updated successfully")

    # Reset the quantity (put it back)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "update", "stock_name": "BoarCo", "quantity_change": 1}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)


def test_insufficient_quantity():
    print("\nTest: Updating with insufficient quantity")

    # First get current quantity
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "lookup", "stock_name": "MenhirCo"}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))
        initial_quantity = result["data"]["quantity"]

    # Try to update with more than available
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {
            "action": "update",
            "stock_name": "MenhirCo",
            "quantity_change": -(initial_quantity + 10),
        }
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))

        print(f"Response: {result}")
        assert result["status"] == "error", "Expected error status"
        assert "error" in result, "Expected error in response"
        assert result["error"]["code"] == 400, "Expected 400 error code"
        print("✓ Test passed: Insufficient quantity returns error")


def run_all_tests():
    try:
        test_lookup_stock()
        test_lookup_nonexistent_stock()
        test_update_quantity()
        test_insufficient_quantity()
        print("\n✓ All catalog service tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")


"""
End AI-assisted code piece
"""


if __name__ == "__main__":
    run_all_tests()
