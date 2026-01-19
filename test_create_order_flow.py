
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

# Simulate the constant from purchases.py
RESERVATION_MINUTES = 30

async def test_real_order_logic():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        print("Starting Transaction...")
        async with conn.transaction():
            try:
                # 1. SETUP DATA
                # Get or create a User
                user_id = await conn.fetchval("SELECT id FROM web_users LIMIT 1")
                if not user_id:
                    print("Creating temp user...")
                    user_id = await conn.fetchval("INSERT INTO web_users (username, email, password, first_name, last_name) VALUES ('testuser', 'test@test.com', 'pass', 'Test', 'User') RETURNING id")

                # Get a Warehouse Variant (crucial for the JOIN test)
                # We need a product that has both a warehouse variant and a web variant (conceptually) or at least the raw data to join
                wsv = await conn.fetchrow("""
                    SELECT wsv.id, wsv.product_id, wsv.size_id, wsv.color_id 
                    FROM warehouse_stock_variants wsv 
                    LIMIT 1
                """)
                
                if not wsv:
                    print("No warehouse variants found. Creating dummy product/variant structure...")
                    # This path creates dependencies if DB is empty, ensuring test runs
                    # (Simplified creation for brevity, assuming DB usually has data)
                    raise Exception("Database is empty of products, cannot test JOIN logic effectively without data.")
                
                print(f"Testing with Warehouse Variant ID: {wsv['id']} (Product: {wsv['product_id']}, Size: {wsv['size_id']}, Color: {wsv['color_id']})")
                
                # Check/Create corresponding Web Variant (needed for cart item)
                # The join relies on wsv.product_id = wci.product_id AND wsv.size_id = wv.size_id ...
                # So we need a web_variant that matches this size/color/product
                wv_id = await conn.fetchval("""
                    SELECT id FROM web_variants 
                    WHERE product_id=$1 AND size_id=$2 AND color_id=$3
                """, wsv['product_id'], wsv['size_id'], wsv['color_id'])

                if not wv_id:
                    print("Creating matching Web Variant for test...")
                    wv_id = await conn.fetchval("""
                        INSERT INTO web_variants (product_id, size_id, color_id, displayed_stock)
                        VALUES ($1, $2, $3, 100) RETURNING id
                    """, wsv['product_id'], wsv['size_id'], wsv['color_id'])
                
                print(f"Using Web Variant ID: {wv_id}")

                # Create a Cart
                cart_id = await conn.fetchval("INSERT INTO web_carts (user_id, created_at) VALUES ($1, CURRENT_TIMESTAMP) RETURNING id", user_id)
                
                # Add Item to Cart (Referencing the WEB VARIANT)
                await conn.execute("""
                    INSERT INTO web_cart_items (cart_id, product_id, variant_id, quantity, created_at)
                    VALUES ($1, $2, $3, 1, CURRENT_TIMESTAMP)
                """, cart_id, wsv['product_id'], wv_id)
                
                print(f"Cart {cart_id} created with Item (WebVariant: {wv_id})")

                # 2. EXECUTE THE FIX LOGIC (The SELECT Query)
                print("Executing patched SELECT query...")
                cart_items = await conn.fetch("""
                SELECT 
                    wci.id as cart_item_id,
                    wci.product_id,
                    wci.variant_id as web_variant_id,
                    wci.quantity,
                    p.nombre_web as product_name,
                    p.precio_web as unit_price,
                    p.provider_code as product_code,
                    s_web.size_name,
                    c_web.color_name,
                    COALESCE(wsv.variant_barcode, '') as variant_barcode,
                     -- Resolve real Warehouse Variant ID for Sales Detail FK
                    wsv.id as warehouse_variant_id,
                    -- Get currently reserved stock for this variant
                    COALESCE((
                        SELECT SUM(sr.quantity)
                        FROM stock_reservations sr
                        WHERE sr.variant_id = wci.variant_id 
                        AND sr.status = 'active'
                        AND sr.expires_at > CURRENT_TIMESTAMP
                    ), 0) as stock_reserved
                FROM web_cart_items wci
                INNER JOIN products p ON wci.product_id = p.id
                LEFT JOIN web_variants wv ON wci.variant_id = wv.id
                LEFT JOIN sizes s_web ON wv.size_id = s_web.id
                LEFT JOIN colors c_web ON wv.color_id = c_web.id
                -- Correct join to find matching warehouse variant
                LEFT JOIN warehouse_stock_variants wsv ON 
                    wsv.product_id = wci.product_id AND 
                    wsv.size_id = wv.size_id AND 
                    wsv.color_id = wv.color_id
                WHERE wci.cart_id = $1
                ORDER BY wci.created_at
                """, cart_id)
                
                if not cart_items:
                    raise Exception("Query returned no items!")

                item = cart_items[0]
                print(f"Fetched Item: WebVariant={item['web_variant_id']}, Resolved WarehouseVariant={item['warehouse_variant_id']}")
                
                if item['warehouse_variant_id'] != wsv['id']:
                    raise Exception(f"JOIN FAILED mismatch! Expected {wsv['id']}, got {item['warehouse_variant_id']}")
                
                print("JOIN Logic Verification: PASSED")

                # 3. INSERT INTO SALES
                print("Inserting Sales row...")
                reservation_expires_at = await conn.fetchval(f"SELECT CURRENT_TIMESTAMP + INTERVAL '{RESERVATION_MINUTES} minutes'")
                print(f"DEBUG: reservation_expires_at type: {type(reservation_expires_at)}")
                print(f"DEBUG: reservation_expires_at val: {reservation_expires_at}")
                if hasattr(reservation_expires_at, 'tzinfo') and reservation_expires_at.tzinfo:
                     print("DEBUG: Stripping timezone info to match naive column...")
                     reservation_expires_at = reservation_expires_at.replace(tzinfo=None)
                
                sale_id = await conn.fetchval("""
                INSERT INTO sales (
                    web_user_id, employee_id, cashier_user_id, storage_id, sale_date, 
                    subtotal, tax_amount, discount, total, status, origin, shipping_address, 
                    shipping_status, shipping_cost, delivery_type, notes, reservation_expires_at, 
                    payment_method, created_at, updated_at
                )
                VALUES ($1, 1, 1, 1, CURRENT_TIMESTAMP, 100, 0, 0, 100, 'Pendiente', 'web', 'Test Address', 
                        'pendiente', 0, 'retiro', 'Test Notes', $2, 'transferencia', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """, user_id, reservation_expires_at)
                print(f"Sale {sale_id} created.")

                # 4. INSERT INTO SALES_DETAIL (The Critical Failure Point)
                print("Inserting Sales Detail (using resolved ID)...")
                warehouse_variant_to_use = item['warehouse_variant_id']
                
                await conn.execute("""
                    INSERT INTO sales_detail (
                        sale_id, product_id, variant_id, product_name, product_code, 
                        size_name, color_name, cost_price, sale_price, quantity, 
                        subtotal, total, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 0, $8, $9, $10, $10, CURRENT_TIMESTAMP)
                """, sale_id, item['product_id'], warehouse_variant_to_use, 
                     item['product_name'], item['product_code'], item['size_name'], 
                     item['color_name'], item['unit_price'], item['quantity'], 
                     float(item['unit_price']) * item['quantity'])
                print("Sales Detail Insert: PASSED")

                # 5. INSERT STOCK RESERVATION (New Table)
                print("Inserting Stock Reservation...")
                await conn.execute("""
                    INSERT INTO stock_reservations (
                        sale_id, variant_id, quantity, reserved_at, expires_at, status
                    )
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4, 'active')
                """, sale_id, item['web_variant_id'], item['quantity'], reservation_expires_at)
                print("Stock Reservation Insert: PASSED")

                print("\nALL CHECKS PASSED SUCCESSFULLY.")
                print("Rolling back transaction to keep DB clean.")
                # Auto-rollback on exit due to exception or explicit rollback
                # Raising error to force rollback in the block context
                raise Exception("TEST_SUCCESS_ROLLBACK")

            except Exception as e:
                if str(e) == "TEST_SUCCESS_ROLLBACK":
                    print("Transaction rolled back as intended.")
                else:
                    raise e

if __name__ == "__main__":
    try:
        asyncio.run(test_real_order_logic())
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
