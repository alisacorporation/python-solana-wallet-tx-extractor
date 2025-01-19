import json
import time
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.rpc.core import RPCException

# Initialize the Solana client
client = Client("https://api.mainnet-beta.solana.com")


def load_wallet_addresses(filename):
    try:
        with open(filename, "r") as file:
            data = json.load(file)
            return data.get("wallet_addresses", [])
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filename}")
        return []


def get_wallet_transactions(wallet_address):
    max_retries = 3
    base_wait_time = 2

    for attempt in range(max_retries):
        try:
            response = client.get_signatures_for_address(wallet_address, limit=10)
            if hasattr(response, "status_code"):
                print(f"Response status: {response.status_code}")
            return response.get("result", [])
        except RPCException as e:
            wait_time = base_wait_time * (attempt + 1)
            print(f"RPC Error for {wallet_address}:")
            print(f"Error message: {str(e)}")
            print(f"Error details: {repr(e)}")
            if hasattr(e, "response"):
                print(
                    f"Response status: {e.response.status_code if e.response else 'No status'}"
                )
                print(
                    f"Response text: {e.response.text if e.response else 'No response text'}"
                )
            print(
                f"Attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds..."
            )
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                return []
        except Exception as e:
            print(f"Unexpected error for {wallet_address}:")
            print(f"Error type: {e.__class__.__name__}")
            print(f"Error message: {str(e)}")
            print(f"Error details: {repr(e)}")
            if hasattr(e, "response"):
                print(
                    f"Response status: {e.response.status_code if e.response else 'No status'}"
                )
                print(
                    f"Response text: {e.response.text if e.response else 'No response text'}"
                )
            if "429" in str(e):
                wait_time = base_wait_time * (attempt + 1)
                print(f"Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            return []


def update_wallet_history(address, transactions=None, error=""):
    try:
        # Read existing data
        with open("wallet_history.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"timestamp": "", "addresses": []}

    # Update timestamp
    data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S.%f")

    # Find and update or add new address entry
    address_entry = next(
        (item for item in data["addresses"] if item["address"] == address), None
    )
    if address_entry:
        address_entry["transactions"] = transactions if transactions else []
        address_entry["error"] = str(error)
    else:
        data["addresses"].append(
            {
                "address": address,
                "transactions": transactions if transactions else [],
                "error": str(error),
            }
        )

    # Write updated data back to file
    with open("wallet_history.json", "w") as file:
        json.dump(data, file, indent=4)


def main():
    # Read wallet addresses from JSON file
    wallet_addresses = load_wallet_addresses("wallet_addresses.json")
    if not wallet_addresses:
        print("No wallet addresses found. Exiting...")
        return

    # Process each wallet address
    for address in wallet_addresses:
        try:
            wallet_address = PublicKey(address)
            print(f"\nProcessing wallet: {address}")

            # Get the last 10 transactions
            signatures = get_wallet_transactions(wallet_address)
            if signatures:
                print(f"Latest transactions for {address}:")
                print(signatures)
                update_wallet_history(address, transactions=signatures)
            else:
                print(f"No transactions found for {address}")
                update_wallet_history(address, error="No transactions found")

            # Increase delay to avoid rate limiting
            time.sleep(5)

        except ValueError as e:
            print(f"Invalid wallet address {address}: {str(e)}")
            update_wallet_history(address, error=str(e))
            continue


if __name__ == "__main__":
    main()
