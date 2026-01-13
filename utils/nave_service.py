import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variables for caching
_cached_token = None
_token_expiry = 0

def get_nave_token() -> str:
    """
    Authenticates with the Nave API and returns the access token.
    Uses in-memory caching to avoid frequent requests.
    
    Returns:
        str: The access token.
        
    Raises:
        Exception: If the request fails or the token cannot be retrieved.
    """
    global _cached_token, _token_expiry
    
    current_time = time.time()
    
    # Return cached token if valid (with 60s buffer)
    if _cached_token and current_time < (_token_expiry - 60):
        return _cached_token

    try:
        client_id = os.getenv("NAVE_CLIENT_ID")
        client_secret = os.getenv("NAVE_CLIENT_SECRET")
        audience = os.getenv("NAVE_AUDIENCE")
        auth_url = os.getenv("NAVE_AUTH_URL_TEST")

        if not all([client_id, client_secret, audience, auth_url]):
            missing_vars = [var for var in ["NAVE_CLIENT_ID", "NAVE_CLIENT_SECRET", "NAVE_AUDIENCE", "NAVE_AUTH_URL_TEST"] if not os.getenv(var)]
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,
            "grant_type": "client_credentials"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(auth_url, json=payload, headers=headers)
        response.raise_for_status()  
        
        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)  # Default to 1 hour if not provided

        if not access_token:
            raise ValueError("Response did not contain an access_token")

        # Update cache
        _cached_token = access_token
        _token_expiry = current_time + expires_in

        return access_token

    except requests.RequestException as e:
        error_msg = f"Failed to connect to Nave API: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
             error_msg += f"\nResponse Body: {e.response.text}"
        raise Exception(error_msg)
    except ValueError as e:
        raise Exception(f"Configuration or Data Error: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

def create_payment_preference(payment_data: dict) -> str:
    """
    Creates a payment preference in Nave.
    
    Args:
        payment_data (dict): Dictionary containing amount details.
                             Expected structure: {"amount": {"currency": "ARS", "value": 100.50}, ...}
    
    Returns:
        str: The checkout URL (checkout_url).
    """
    try:
        token = get_nave_token()
        
        payment_url = os.getenv("NAVE_PAYMENT_URL_TEST")
        platform = os.getenv("NAVE_PLATFORM")
        store_id = os.getenv("NAVE_STORE_ID")
        callback_url = os.getenv("MY_CALLBACK_URL")
        notification_url = os.getenv("MY_NOTIFICATION_URL")
        
        if not all([payment_url, platform, store_id, callback_url, notification_url]):
             missing_vars = [var for var in ["NAVE_PAYMENT_URL_TEST", "NAVE_PLATFORM", "NAVE_STORE_ID", "MY_CALLBACK_URL", "MY_NOTIFICATION_URL"] if not os.getenv(var)]
             raise ValueError(f"Missing environment variables for payment creation: {', '.join(missing_vars)}")

        # Construct payload
        # Ensure 'amount' is present in payment_data
        if "amount" not in payment_data:
            raise ValueError("Payment data must include 'amount'")

        # Merge payment_data with required environment configs
        payload = {
            "platform": platform,
            "store_id": store_id,
            "callback_url": callback_url,
            "notification_url": notification_url,
            **payment_data # Includes amount, consumer, etc. passed from the route
        }
        
        # Ensure consumer dummy data if not present (handled by caller optimally, but safe guarding here if needed? 
        # The prompt says: "consumer (datos dummy si no existen)". 
        # I'll check if consumer is in payment_data, if not add dummy.
        if "consumer" not in payload:
            payload["consumer"] = {
                "name": "Consumidor Final",
                "email": "test@example.com"
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(payment_url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        checkout_url = data.get("checkout_url")
        
        if not checkout_url:
             # Some APIs might return it differently, but prompt says returns checkout_url
             raise ValueError("Response did not contain checkout_url")
             
        return checkout_url

    except requests.RequestException as e:
        error_msg = f"Failed to create payment preference: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
             error_msg += f"\nResponse Body: {e.response.text}"
        raise Exception(error_msg)
    except Exception as e:
        raise Exception(f"Error creating payment preference: {str(e)}")

if __name__ == "__main__":
    # Simple test if run directly
    try:
        print("Testing Token Retrieval...")
        token = get_nave_token()
        print(f"Token: {token[:20]}...")
        
        # Uncomment to test payment creation if env vars are set
        # print("Testing Payment Creation...")
        # url = create_payment_preference({"amount": {"currency": "ARS", "value": 100}, "consumer": {"name": "Test User"}})
        # print(f"Checkout URL: {url}")
        
    except Exception as e:
        print(f"Error: {e}")
