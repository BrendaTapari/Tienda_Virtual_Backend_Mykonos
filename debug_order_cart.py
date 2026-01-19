import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from config.db_connection import DatabaseManager, db

async def check_recent_order():
    try:
        await DatabaseManager.initialize()
        
        # Get the most recent order
        query = """
            SELECT id, web_user_id, status, shipping_status, created_at 
            FROM sales 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        order = await db.fetch_one(query)
        
        if order:
            print(f"Recent Order ID: {order['id']}")
            print(f"Web User ID: {order['web_user_id']}")
            print(f"Status: {order['status']}")
            
            if order['web_user_id']:
                # Check if this user has a cart
                cart = await db.fetch_one("SELECT id FROM web_carts WHERE user_id = $1", order['web_user_id'])
                if cart:
                    print(f"User has cart ID: {cart['id']}")
                    # Check items in cart
                    items = await db.fetch_all("SELECT * FROM web_cart_items WHERE cart_id = $1", cart['id'])
                    print(f"Items remaining in cart: {len(items)}")
                    for item in items:
                        print(f"  - Item ID: {item['id']}, Product ID: {item['web_variant_id']}, Qty: {item['quantity']}")
                else:
                    print("User has NO cart found.")
            else:
                print("WARNING: Order has no web_user_id linked!")
        else:
            print("No orders found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(check_recent_order())
