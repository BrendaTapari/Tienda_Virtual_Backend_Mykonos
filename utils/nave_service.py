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
        # Prioritize SANDBOX credentials if available
        client_id = os.getenv("NAVE_CLIENT_ID_SANDBOX") or os.getenv("NAVE_CLIENT_ID")
        client_secret = os.getenv("NAVE_CLIENT_SECRET_SANDBOX") or os.getenv("NAVE_CLIENT_SECRET")
        
        # Enforce correct defaults for Ranty Sandbox if not in env
        audience = os.getenv("NAVE_AUDIENCE", "https://naranja.com/ranty/merchants/api")
        
        # Determine Auth URL based on credentials (heuristic: if Sandbox creds used, use Test URL)
        # Or simple priority: defined TEST url -> defined PROD url -> default
        if os.getenv("NAVE_CLIENT_ID_SANDBOX"):
            auth_url = os.getenv("NAVE_AUTH_URL_TEST", "https://homoservices.apinaranja.com/security-ms/api/security/auth0/b2b/m2msPrivate")
        else:
            # Fallback to previous logic (Prod priority if verified, etc)
            auth_url = os.getenv("NAVE_AUTH_URL_PROD") or os.getenv("NAVE_AUTH_URL_TEST") or "https://homoservices.apinaranja.com/security-ms/api/security/auth0/b2b/m2msPrivate"

        if not all([client_id, client_secret]):
            missing_vars = [var for var in ["NAVE_CLIENT_ID (or _SANDBOX)", "NAVE_CLIENT_SECRET (or _SANDBOX)"] if not client_id or not client_secret]
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(auth_url, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
             # Enhance error message with response body for debugging 401s
             raise Exception(f"Auth Failed ({e.response.status_code}): {e.response.text}") from e
        
        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)  # Default to 1 hour if not provided

        if not access_token:
            raise ValueError("Response did not contain an access_token")

        # Update cache
        _cached_token = access_token
        _token_expiry = current_time + float(expires_in)

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
    Creates a payment preference in Nave/Ranty using the new e-commerce endpoint.
    
    Args:
        payment_data (dict): Dictionary containing payment details.
                             Expected keys: 'amount', 'consumer' (optional), 
                             'items' (optional list of products), 'external_payment_id' (optional).
    
    Returns:
        str: The checkout URL (checkout_url).
    """
    try:
        # Note: Depending on the specific authentication flow for this new endpoint,
        # we might need the token or it might use API keys directly. 
        # The user's curl example implies "Authorization: Bearer <token>", so we get the token.
        token = get_nave_token()
        
        # New Endpoint
        payment_url = "https://api-sandbox.ranty.io/api/payment_request/ecommerce"
        
        # Env vars - Prioritize Test POS ID if available
        pos_id = os.getenv("POS_ID_TEST") or os.getenv("POS_ID")
        callback_url = os.getenv("MY_CALLBACK_URL")
        
        if not pos_id:
             raise ValueError("Missing environment variable: POS_ID or POS_ID_TEST")

        # Extract data
        amount_data = payment_data.get("amount", {})
        currency = amount_data.get("currency", "ARS")
        value = amount_data.get("value")
        
        if not value:
            raise ValueError("Payment amount value is required")

        # Generate unique external ID if not provided
        external_id = payment_data.get("external_payment_id", f"order-{int(time.time())}")

        # Construct Buyer
        consumer = payment_data.get("consumer", {})
        buyer = {
            "doc_type": consumer.get("doc_type", "DNI"),
            "doc_number": consumer.get("doc_number", "11111111"), # Dummy if missing
            "name": consumer.get("name", "Consumidor Final"),
            "user_email": consumer.get("email", "test@example.com"),
            "user_id": consumer.get("id", "guest_user"),
            "billing_address": {
                "street_1": "Street 123", # Dummy defaults required by API?
                "street_2": "N/A",
                "city": "Capital Federal",
                "region": "Buenos Aires",
                "country": "AR",
                "zipcode": "1000"
            }
        }

        # Construct Items/Products
        # If 'items' is passed, map them. Otherwise create a single item for the total amount.
        products = []
        if "items" in payment_data and payment_data["items"]:
            for item in payment_data["items"]:
                products.append({
                    "name": item.get("name", "Producto"),
                    "description": item.get("description", "Descripción"),
                    "quantity": item.get("quantity", 1),
                    "unit_price": {
                        "currency": currency,
                        "value": f"{float(item.get('unit_price', value)):.2f}" # Force 2 decimal places
                    }
                })
        else:
            # Fallback item
            products.append({
                "name": "Compra Online",
                "description": "Pago General",
                "quantity": 1,
                "unit_price": {
                    "currency": currency,
                    "value": str(value)
                }
            })

        # Construct Payload based on User's format
        payload = {
            "external_payment_id": external_id,
            "seller": {
                "pos_id": pos_id
            },
            "transactions": [
                {
                    "amount": {
                        "currency": currency,
                        "value": f"{float(value):.2f}" # Force 2 decimal places string
                    },
                    "products": products
                }
            ],
            "buyer": buyer,
            "additional_info": {
                "callback_url": callback_url or "https://google.com" # Fallback if env var missing
            },
            "duration_time": 3000
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(payment_url, json=payload, headers=headers)
        
        # Print response if error occurs (keeping this for safety logs)
        if response.status_code >= 400:
             # Basic logging for errors is good practice, but removing the verbose checks
             print(f"ERROR Nave Payment ({response.status_code}): {response.text}")

        response.raise_for_status()
        
        data = response.json()
        
        # Updated to simpler structure based on user feedback
        checkout_url = data.get("checkout_url")
        
        if not checkout_url:
             raise ValueError(f"Could not find checkout_url in response: {data}")
             
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
