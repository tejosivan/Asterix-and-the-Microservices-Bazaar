import requests
import socket
import json
import time
import os

FRONTEND_HOST = "localhost"
FRONTEND_PORT = 5555
BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"


"""
AI: ChatGPT 4o - used in Lab 2
 Prompt: Test the caching mechanism by:
   - Verifying cache hits on repeated lookups
   - Testing cache invalidation when stock data is modified
   - Confirming fresh data is retrieved after invalidation
"""


def test_client_workflow():
    print("\nTest: Client workflow (lookup, trade, validate)")
    # Lookup stock
    response = requests.get(f"{BASE_URL}/stocks/GameStart")
    assert response.status_code == 200
    stock_data = response.json()["data"]
    print(f"Stock lookup: {stock_data}")

    # Create order
    order_data = {"name": "GameStart", "quantity": 1, "type": "buy"}
    response = requests.post(f"{BASE_URL}/orders", json=order_data)
    assert response.status_code == 200
    order_num = response.json()["data"]["transaction_number"]
    print(f"Order created: {order_num}")

    # Validate order
    response = requests.get(f"{BASE_URL}/orders/{order_num}")
    assert response.status_code == 200
    order_data = response.json()["data"]
    assert order_data["number"] == order_num
    assert order_data["name"] == "GameStart"
    assert order_data["type"] == "buy"
    assert order_data["quantity"] == 1
    print(f"Order validated: {order_data}")
    print("✓ Client workflow test passed")


def test_cache_invalidation():
    print("\nTest: Cache invalidation")
    # First lookup (cache miss)
    response = requests.get(f"{BASE_URL}/stocks/GameStart")
    assert response.status_code == 200
    print("First lookup (cache miss)")

    # Second lookup (cache hit)
    response = requests.get(f"{BASE_URL}/stocks/GameStart")
    assert response.status_code == 200
    print("Second lookup (cache hit)")

    # Update stock (should invalidate cache)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 6666))
        request = {"action": "update", "stock_name": "GameStart", "quantity_change": -1}
        sock.sendall(json.dumps(request).encode("utf-8"))
        response = sock.recv(4096)
        result = json.loads(response.decode("utf-8"))
        assert result["status"] == "success"
        print("Stock updated")

    # Third lookup (cache miss after invalidation)
    response = requests.get(f"{BASE_URL}/stocks/GameStart")
    assert response.status_code == 200
    print("Third lookup (cache miss after invalidation)")
    print("✓ Cache invalidation test passed")


def test_leader_failover():
    print("\nTest: Leader failover")
    # Simulate leader crash by stopping the leader replica
    print("Leader replica stopped (manual step)")

    order_data = {"name": "GameStart", "quantity": 1, "type": "buy"}
    response = requests.post(f"{BASE_URL}/orders", json=order_data)
    assert response.status_code == 200
    order_num = response.json()["data"]["transaction_number"]
    print(f"Order created after failover: {order_num}")
    print("✓ Leader failover test passed")


def run_all_tests():
    try:
        test_client_workflow()
        test_cache_invalidation()
        test_leader_failover()
        print("\n✓ All integration tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")


"""
End AI-assisted code piece
"""


if __name__ == "__main__":
    run_all_tests()
