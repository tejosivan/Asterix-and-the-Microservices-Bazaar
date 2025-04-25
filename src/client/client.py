# libraries and setup
import sys
import requests
import random
import time
import os

STOCK_LIST = ["GameStart", "BoarCo", "RottenFishCo", "MenhirCo"]
trades_record = []


# main function
def run_client(p, stock_name):
    print(f"\n\nEstablishing a session for {stock_name}...")
    num_of_trades = 0
    FRONTEND_HOST = os.environ.get("FRONTEND_HOST", "localhost")
    FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5555")
    BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

    # Resources referred:
    # https://docs.python-requests.org/en/latest/user/advanced/#session-objects
    # https://requests.readthedocs.io/en/latest/user/advanced/
    with requests.Session() as session:
        while True:
            time.sleep(1)
            lookup_response = session.get(f"{BASE_URL}/stocks/{stock_name}")
            if lookup_response.status_code == 200:
                response = lookup_response.json()
                price = response["data"]["price"]
                quantity = response["data"]["quantity"]
                print(
                    f"\n\n{stock_name} lookup results: \n Price = {price} \n Quantity = {quantity}"
                )
                if quantity > 0:
                    request_data = {"name": stock_name, "quantity": 1, "type": "sell"}
                    trade_response = session.post(
                        f"{BASE_URL}/orders", json=request_data
                    )
                    if trade_response.status_code == 200:
                        resp = trade_response.json()
                        transaction_number = resp["data"]["transaction_number"]
                        print(
                            f"\n\nOne stock purchased of {stock_name}, transaction_number = {transaction_number}"
                        )
                        num_of_trades += 1
                        record = {
                            "order_number": transaction_number,
                            "stock_name": stock_name,
                            "type": "sell",
                            "quantity": 1
                        }
                        trades_record.append(record)
                    else:
                        print("\n\nTrade Failed, exiting")
                        break
                else:
                    print("No stock quantity left! Exiting session")
                    break
            else:
                if lookup_response.status_code == 404:
                    print("Error: Stock not found!")
            if random.random() > p:
                print(f"\n\nEnd session. {num_of_trades} trades were made.")
                print("debug 1")
                break

        print("debug 2")             
        # validation block
        ''' to test error
        faulty_record = {
                            "order_number": 12345,
                            "stock_name": "GameStart",
                            "type": "sell",
                            "quantity": 1
                        }
        trades_record.append(faulty_record)'''
        for trade in trades_record:
            transaction_number = trade["order_number"]
            validation_resp = session.get(
                f"{BASE_URL}/orders/{transaction_number}"
                    )
            if validation_resp.status_code == 200:
                server_copy_trade = validation_resp.json()["data"]
                if (server_copy_trade["name"] == trade["stock_name"] and server_copy_trade["type"] == trade["type"] and server_copy_trade["quantity"] == trade["quantity"]):
                    print(f"Transaction {transaction_number} correctly verified.")
                else:
                    print(f"Transaction {transaction_number} doesn't match the server's order.")
            else:
                print("error validating")    


# driver code
if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            p = float(sys.argv[1])
            if not 0 <= p <= 1:
                print("P needs to be in [0,1], defaulting to 0.8")
                p = 0.8
        except ValueError:
            print("P should be a float! Defaulting to 0.8")
            p = 0.8
    else:
        p = 0.8
        
    # pick a random stock
    stock_name = random.choice(STOCK_LIST)
    run_client(p, stock_name)
