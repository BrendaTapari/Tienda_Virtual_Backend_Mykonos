
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def test_full_order_flow():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    print("Testing FULL ORDER FLOW...")
    
    # Mock data
    web_user_id = 1 # Assuming user 1 exists
    async with pool.acquire() as conn:
        try:
             async with conn.transaction():
                # 1. Fetch user to confirm existence
                user_exists = await conn.fetchval("SELECT id FROM users WHERE id = $1", web_user_id)
                if not user_exists:
                    web_user_id = await conn.fetchval("SELECT id FROM users LIMIT 1")
                    print(f"Switched to user {web_user_id}")

                # 2. INSERT SALE (Using fixed legacy IDs)
                print("Inserting SALE...")
                sale_id = await conn.fetchval(
                    """
                    INSERT INTO sales (
                        web_user_id,
                        employee_id,
                        cashier_user_id,
                        storage_id,
                        sale_date,
                        subtotal,
                        tax_amount,
                        discount,
                        total,
                        status,
                        origin,
                        shipping_address,
                        shipping_status,
                        shipping_cost,
                        delivery_type,
                        notes,
                        reservation_expires_at,
                        payment_method,
                        created_at,
                        updated_at
                    )
                    VALUES ($1, 1, 1, 1, CURRENT_TIMESTAMP, $2, 0, 0, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                    """,
                    web_user_id,
                    1500.0,
                    1500.0,
                    'Pendiente',
                    'web',
                    'Calle Falsa 123',
                    'pendiente',
                    0.0,
                    'retiro',
                    'Test Notes',
                    None, # reservation_expires_at (assuming we use expression in real code, but here testing null or value)
                    'transferencia'
                )
                print(f"Sale inserted: {sale_id}")

                # 3. INSERT SALE DETAIL
                print("Inserting SALE DETAIL...")
                # Try to get a real product first
                product_row = await conn.fetchrow("SELECT id, product_name FROM products LIMIT 1")
                if not product_row: raise Exception("No products found")
                
                # Try to get a variant? Assuming manual mock for now
                variant_id = 999999 # Might fail if FK exists
                # Let's check constraints. sales_detail usually references products. variant_id seems optional or FK.
                
                sale_detail_id = await conn.fetchval(
                    """
                    INSERT INTO sales_detail (
                        sale_id,
                        product_id,
                        variant_id,
                        product_name,
                        product_code,
                        size_name,
                        color_name,
                        cost_price,
                        sale_price,
                        quantity,
                        discount_percentage,
                        discount_amount,
                        tax_percentage,
                        tax_amount,
                        subtotal,
                        total,
                        created_at
                    )
                    VALUES ($1, $2, $3, $4, 'CODE123', 'M', 'Rojo', 0, 1500, 1, 0, 0, 0, 0, 1500, 1500, CURRENT_TIMESTAMP)
                    RETURNING id
                    """,
                    sale_id,
                    product_row['id'],
                    1, # Using 1 as variant_id mock
                    product_row['product_name']
                )
                print(f"Sale Detail inserted: {sale_detail_id}")

                # 4. INSERT STOCK RESERVATION
                print("Inserting STOCK RESERVATION...")
                await conn.execute(
                    """
                    INSERT INTO stock_reservations (
                        sale_id,
                        variant_id,
                        quantity,
                        reserved_at,
                        expires_at,
                        status
                    )
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 minutes', 'active')
                    """,
                    sale_id,
                    1, # variant_id
                    1
                )
                print("Stock reservation inserted.")

                # 5. INSERT TRACKING
                print("Inserting TRACKING...")
                await conn.execute(
                    """
                    INSERT INTO sales_tracking_history (
                        sale_id,
                        status,
                        description,
                        location,
                        changed_by_user_id,
                        created_at
                    )
                    VALUES ($1, $2, $3, $4, NULL, CURRENT_TIMESTAMP)
                    """,
                    sale_id,
                    'pendiente',
                    'Pedido creado.',
                    'Sistema Web',
                )
                print("Tracking inserted.")
                
                print("ROLLING BACK...")
                raise Exception("Test Passed (Rolling back)")

        except Exception as e:
            if "Test Passed" in str(e):
                print(e)
            else:
                print(f"FAILURE: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_full_order_flow())
