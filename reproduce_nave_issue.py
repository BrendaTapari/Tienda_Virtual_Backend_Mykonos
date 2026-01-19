import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.nave_service import create_payment_preference, get_nave_token

def test_nave_connection():
    load_dotenv()
    
    print("Checking Environment Variables...")
    pos_id = os.getenv("POS_ID_TEST") or os.getenv("POS_ID")
    print(f"POS_ID: {pos_id}")
    nave_store_id = os.getenv("NAVE_STORE_ID")
    print(f"NAVE_STORE_ID: {nave_store_id}")
    
    callback_url = os.getenv("MY_CALLBACK_URL")
    notification_url = os.getenv("MY_NOTIFICATION_URL")
    print(f"MY_CALLBACK_URL (Redirect): {callback_url}")
    print(f"MY_NOTIFICATION_URL (Webhook): {notification_url}")
    
    if not pos_id and nave_store_id:
        print("POS_ID missing, but NAVE_STORE_ID present. Code expects POS_ID. This might be the issue if not set in server env.")
    
    print("\nTesting Token Retrieval...")
    try:
        token = get_nave_token()
        print(f"Token retrieved successfully: {token[:20]}...")
    except Exception as e:
        print(f"Failed to get token: {e}")
        return

    print("\nTesting Payment Creation...")
    payment_data = {
        "amount": {"currency": "ARS", "value": 150.50},
        "consumer": {
            "name": "Test User",
            "email": "test@example.com",
            "doc_type": "DNI",
            "doc_number": "12345678"
        },
        "items": [
            {
                "name": "Test Product",
                "description": "A product for testing",
                "quantity": 1,
                "unit_price": 150.50
            }
        ]
    }
    
    try:
        result = create_payment_preference(payment_data)
        print("Payment Creation Successful!")
        print(result)
    except Exception as e:
        print(f"Payment Creation Failed: {e}")

if __name__ == "__main__":
    test_nave_connection()
