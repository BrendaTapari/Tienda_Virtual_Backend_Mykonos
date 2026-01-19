import asyncio
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from utils.email import send_ready_for_pickup_email, fastmail

async def main():
    print("Testing send_ready_for_pickup_email with REAL module imports...")
    
    # Create an AsyncMock-like wrapper for the send_message method
    async def mock_send_message(message):
        # Store the message for verification
        mock_send_message.called = True
        mock_send_message.call_args = (message,)
        return True
    
    mock_send_message.called = False
    mock_send_message.call_args = None
    
    # Replace the method on the instance
    fastmail.send_message = mock_send_message
    
    email = "test@example.com"
    username = "Test User"
    order_id = 12345
    
    try:
        await send_ready_for_pickup_email(email, username, order_id)
        
        if fastmail.send_message.called:
            print("SUCCESS: fastmail.send_message was called")
            message = fastmail.send_message.call_args[0]
            
            print(f"Subject: {message.subject}")
            print(f"Recipients: {message.recipients}")
            body_str = str(message.body)
            
            if "¡Tu pedido está listo!" in body_str:
                 print("Body check: PASSED")
            else:
                 print(f"Body check: FAILED. Body snippet: {body_str[:100]}...")
            
            if "San Luis 887" in body_str:
                print("Address interpolation: PASSED")
            else:
                print("Address interpolation: FAILED")
                
        else:
            print("FAILURE: fastmail.send_message was NOT called")
            
    except Exception as e:
        print(f"CRITICAL FAILURE during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
