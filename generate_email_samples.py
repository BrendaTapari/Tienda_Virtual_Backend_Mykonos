import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add the project directory to sys.path
sys.path.append(os.getcwd())

# Mock environment variables before importing utils.email
os.environ["FRONTEND_URL"] = "https://mykonosboutique.com.ar"
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "password"
os.environ["MAIL_FROM"] = "test@example.com"

# Import utils.email which initializes fastmail
import utils.email

# Mock the fastmail instance's send_message method
async def mock_send_message(message):
    print(f"--- Captured Email: {message.subject} ---")
    # Clean filename
    safe_subject = "".join([c if c.isalnum() else "_" for c in message.subject])
    filename = f"email_sample_{safe_subject}.html"
    with open(filename, "w") as f:
        f.write(message.body)
    print(f"Saved to {filename}")

# Patch the send_message method on the global fastmail object
utils.email.fastmail.send_message = mock_send_message

async def generate_samples():
    print("Generating samples...")
    
    # Registration Email
    print("\nGenerating Registration Email...")
    try:
        await utils.email.send_verification_email("test@example.com", "TestUser", "sample-token")
    except Exception as e:
        print(f"Error generating registration email: {e}")

    # Contact Email
    print("\nGenerating Contact Email...")
    try:
        await utils.email.send_contact_email(name="Sender Name", email="sender@example.com", phone="123456", message_text="This is a contact message.\nIt has multiple lines.\n    And indentation.")
    except Exception as e:
        print(f"Error generating contact email: {e}")
        
    # Broadcast Email
    print("\nGenerating Broadcast Email...")
    try:
        await utils.email.send_broadcast_email(
            recipients=["test@example.com"], 
            title="Broadcast Title", 
            message_text="This is the message body.\n    It should handle indentation correctly.\nNo crazy whitespace.", 
            link_url="/store", 
            image_url="https://example.com/image.png"
        )
    except Exception as e:
        print(f"Error generating broadcast email: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(generate_samples())
