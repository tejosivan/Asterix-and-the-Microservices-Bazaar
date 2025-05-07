"""
AI: ChatGPT 4o - used in Lab 2
 Prompt: I need help to work on Test Cases for Integration
"""

import socket
import json
import time
import os

ORDER_HOST = "localhost"
ORDER_PORT = 7777


def send_request(request):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ORDER_HOST, ORDER_PORT))
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        return json.loads(response.decode("utf-8"))


def test_ping_service():
    print("\nTest: Ping the order service")
    request = {"action": "ping"}
    response = send_request(request)
    print(f"Response: {response}")
    assert response["status"] == "success"
    print("✓ Ping test passed")


def test_trade_and_lookup_function():
    print("\nTest: Trade and lookup order")
    # Make a trade
    trade_request = {
        "action": "trade",
        "stock_name": "GameStart",
        "quantity": 1,
        "order_type": "buy",
    }
    trade_response = send_request(trade_request)
    print(f"Trade response: {trade_response}")
    assert trade_response["status"] == "success"
    order_num = trade_response["data"]["transaction_number"]

    # Lookup the order
    lookup_request = {"action": "lookup", "order_number": order_num}
    lookup_response = send_request(lookup_request)
    print(f"Lookup response: {lookup_response}")
    assert lookup_response["status"] == "success"
    assert lookup_response["data"]["number"] == order_num
    assert lookup_response["data"]["name"] == "GameStart"
    assert lookup_response["data"]["type"] == "buy"
    assert lookup_response["data"]["quantity"] == 1
    print("✓ Trade and lookup test passed")


def test_lookup_nonexistent_order_service():
    print("\nTest: Lookup non-existent order service")
    request = {"action": "lookup", "order_number": 999999}
    response = send_request(request)
    print(f"Response: {response}")
    assert response["status"] == "error"
    assert response["error"]["code"] == 404
    print("✓ Non-existent order lookup test passed")


def run_all_tests():
    try:
        test_ping_service()
        test_trade_and_lookup_function()
        test_lookup_nonexistent_order_service()
        print("\n✓ All order service tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")


if __name__ == "__main__":
    run_all_tests()

"""
End AI-assisted code piece
"""
