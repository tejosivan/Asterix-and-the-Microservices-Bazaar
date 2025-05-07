import requests
import json
import time
import os

FRONTEND_HOST = "localhost"
FRONTEND_PORT = 5555
BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"


"""
AI: ChatGPT 4o - used in Lab 2
 Prompt: I need help to work on Test Cases for Frontend Service
"""


def test_stock_lookup():
    print("\nTest: Stock lookup")
    response = requests.get(f"{BASE_URL}/stocks/GameStart")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "data" in response.json()
    assert response.json()["data"]["name"] == "GameStart"
    print("✓ Stock lookup test passed")


def test_order_creation():
    print("\nTest: Order creation")
    order_data = {"name": "GameStart", "quantity": 1, "type": "buy"}
    response = requests.post(f"{BASE_URL}/orders", json=order_data)
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "data" in response.json()
    assert "transaction_number" in response.json()["data"]
    order_num = response.json()["data"]["transaction_number"]
    print("✓ Order creation test passed")
    return order_num


def test_order_lookup(order_num):
    print("\nTest: Order lookup")
    response = requests.get(f"{BASE_URL}/orders/{order_num}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "data" in response.json()
    assert response.json()["data"]["number"] == order_num
    assert response.json()["data"]["name"] == "GameStart"
    assert response.json()["data"]["type"] == "buy"
    assert response.json()["data"]["quantity"] == 1
    print("✓ Order lookup test passed")


def test_lookup_nonexistent_order():
    print("\nTest: Lookup non-existent order")
    response = requests.get(f"{BASE_URL}/orders/999999")
    print(f"Response: {response.json()}")
    assert response.status_code == 404
    assert "error" in response.json()
    print("✓ Non-existent order lookup test passed")


def run_all_tests():
    try:
        test_stock_lookup()
        order_num = test_order_creation()
        test_order_lookup(order_num)
        test_lookup_nonexistent_order()
        print("\n✓ All frontend service tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")


"""
End AI-assisted code piece
"""

if __name__ == "__main__":
    run_all_tests()
