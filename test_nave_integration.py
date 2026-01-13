import sys
import os
import time
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append("/home/breightend/Tienda_Virtual_Backend_Mykonos")

# Mock environment variables
os.environ["NAVE_CLIENT_ID"] = "test_client_id"
os.environ["NAVE_CLIENT_SECRET"] = "test_client_secret"
os.environ["NAVE_AUDIENCE"] = "test_audience"
os.environ["NAVE_AUTH_URL_TEST"] = "https://test.auth.url"
os.environ["NAVE_PAYMENT_URL_TEST"] = "https://test.payment.url"
os.environ["NAVE_PLATFORM"] = "test_platform"
os.environ["NAVE_STORE_ID"] = "test_store_id"
os.environ["MY_CALLBACK_URL"] = "https://my.callback"
os.environ["MY_NOTIFICATION_URL"] = "https://my.notification"

# Import service after mocking env
from utils import nave_service

def test_token_caching():
    print("Testing Token Caching...")
    
    # Mock requests.post
    with patch('requests.post') as mock_post:
        # First call: Returns token
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "token_1", "expires_in": 3600}
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        token1 = nave_service.get_nave_token()
        print(f"Call 1 Token: {token1}")
        assert token1 == "token_1"
        assert mock_post.call_count == 1
        
        # Second call: Should be cached
        token2 = nave_service.get_nave_token()
        print(f"Call 2 Token: {token2}")
        assert token2 == "token_1"
        assert mock_post.call_count == 1 # Still 1, used cache
        
        print("Caching passed!")

def test_payment_creation():
    print("\nTesting Payment Creation...")
    
    with patch('utils.nave_service.get_nave_token', return_value="mocked_token"):
        with patch('requests.post') as mock_post:
             mock_response = MagicMock()
             mock_response.json.return_value = {"checkout_url": "https://nave.com/checkout/123"}
             mock_response.status_code = 200
             mock_post.return_value = mock_response
             
             url = nave_service.create_payment_preference({"amount": {"currency": "ARS", "value": 100}})
             print(f"Checkout URL: {url}")
             assert url == "https://nave.com/checkout/123"
             
             # Verify payload
             args, kwargs = mock_post.call_args
             payload = kwargs['json']
             assert payload['platform'] == "test_platform"
             assert payload['amount']['value'] == 100
             assert payload['consumer']['name'] == "Consumidor Final" # Default value check
             
             print("Payment creation passed!")

if __name__ == "__main__":
    try:
        test_token_caching()
        test_payment_creation()
        print("\nAll tests passed successfully.")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
