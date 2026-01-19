
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.db_connection import DatabaseManager

async def debug_latest_order():
    print("=== DEBUGGING LATEST ORDER ===")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # 1. Get Latest Order (#33 or whatever is latest)
        order = await conn.fetchrow("""
            SELECT id, web_user_id, status, total, created_at 
            FROM sales 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        if not order:
            print("No confirmed orders found.")
            return

        print(f"\nLast Order: ID {order['id']}")
        print(f"User ID: {order['web_user_id']}")
        print(f"Status: {order['status']}")
        print(f"Total: {order['total']}")
        
        # 2. Check Sales Detail
        details = await conn.fetch("""
            SELECT id, product_id, variant_id, quantity, sale_price, product_name 
            FROM sales_detail 
            WHERE sale_id = $1
        """, order['id'])
        
        print(f"\nOrder Items ({len(details)}):")
        for d in details:
            print(f" - Detail ID {d['id']}: Product {d['product_id']}, Variant {d['variant_id']}, Qty {d['quantity']}, Price {d['sale_price']}")
            
            # Check if these point to duplicate data
            # Check the variant
            if d['variant_id']:
                 v = await conn.fetchrow("SELECT * FROM warehouse_stock_variants WHERE id = $1", d['variant_id'])
                 if v:
                     print(f"   -> Linked to Warehouse Variant {v['id']} (Prod {v['product_id']}, Size {v['size_id']}, Color {v['color_id']})")
                 else:
                     print(f"   -> Warehouse Variant {d['variant_id']} NOT FOUND")

        # 3. Check User's Cart (Current State)
        cart = await conn.fetchrow("SELECT id FROM web_carts WHERE user_id = $1", order['web_user_id'])
        if cart:
            print(f"\nUser Cart ID: {cart['id']}")
            cart_items = await conn.fetch("""
                SELECT id, product_id, variant_id, quantity 
                FROM web_cart_items 
                WHERE cart_id = $1
            """, cart['id'])
            
            print(f"Cart Items ({len(cart_items)}):")
            for ci in cart_items:
                print(f" - Cart Item ID {ci['id']}: Product {ci['product_id']}, Variant {ci['variant_id']}, Qty {ci['quantity']}")
        else:
            print("\nUser has no cart.")

        # 4. Check Product 3 Discount Status
        p3 = await conn.fetchrow("SELECT id, nombre_web, precio_web, sale_price, has_discount, discount_percentage FROM products WHERE id = 3")
        if p3:
            print(f"\nProduct 3 Status: {dict(p3)}")

if __name__ == "__main__":
    asyncio.run(debug_latest_order())
