
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def test_interval_query():
    print("Connecting to DB...")
    pool = await DatabaseManager.get_pool()
    
    RESERVATION_MINUTES = 30
    
    print(f"Testing query with RESERVATION_MINUTES = {RESERVATION_MINUTES}")
    
    try:
        # Replicating the suspicious code from routes/purchases.py line 422
        async with pool.acquire() as conn:
            reservation_expires_at = await conn.fetchval(
                "SELECT CURRENT_TIMESTAMP + INTERVAL '%s minutes'",
                RESERVATION_MINUTES
            )
            print(f"Success! Result: {reservation_expires_at}")
    except Exception as e:
        print(f"Caught expected exception: {type(e).__name__}: {e}")
        
    # Also test the fix
    print("\nTesting CORRECTED query:")
    try:
        async with pool.acquire() as conn:
            # Correct way 1: Parameterized
            reservation_expires_at = await conn.fetchval(
                "SELECT CURRENT_TIMESTAMP + ($1 || ' minutes')::interval",
                str(RESERVATION_MINUTES)
            )
            print(f"Fix 1 Result: {reservation_expires_at}")
            
             # Correct way 2: f-string (safe for integer constant)
            reservation_expires_at_2 = await conn.fetchval(
                f"SELECT CURRENT_TIMESTAMP + INTERVAL '{RESERVATION_MINUTES} minutes'"
            )
            print(f"Fix 2 Result: {reservation_expires_at_2}")

    except Exception as e:
        print(f"Fix failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_interval_query())
