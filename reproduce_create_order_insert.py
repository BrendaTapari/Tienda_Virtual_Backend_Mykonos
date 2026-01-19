
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def test_insert_sale():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    print("Testing INSERT into sales table...")
    
    # Mock data based on the route
    web_user_id = 999999 # Non-existent user might fail FK, so we need a real one or handle FK violation
    # Actually, let's try to fetch a real user first
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id FROM web_users LIMIT 1")
        if not user:
            print("No users found to test with.")
            return
        
        web_user_id = user['id']
        print(f"Using web_user_id: {web_user_id}")
        
        query = """
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
                    created_at,
                    updated_at
                )
                VALUES ($1, 1, 1, 1, CURRENT_TIMESTAMP, $2, 0, 0, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP + INTERVAL '30 minutes', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """
        
        args = (
            web_user_id,       # $1
            1000.0,            # $2 subtotal
            1000.0,            # $3 total
            'Pendiente',       # $4
            'web',             # $5
            'Calle Falsa 123', # $6
            'pendiente',       # $7
            0.0,               # $8
            'retiro',          # $9
            'Test Notes'       # $10
        )
        
        try:
            async with conn.transaction(): # Rollback after test
                sale_id = await conn.fetchval(query, *args)
                print(f"Success! Inserted sale_id: {sale_id}")
                raise Exception("Rolling back test transaction") 
        except Exception as e:
            if "Rolling back" in str(e):
                print("Test passed (Transaction rolled back)")
            else:
                print(f"INSERT FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_insert_sale())
