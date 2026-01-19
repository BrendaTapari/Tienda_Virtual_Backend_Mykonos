
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def apply_fix():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    print("Applying schema fix...")
    async with pool.acquire() as conn:
        # Add reservation_expires_at
        try:
            await conn.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS reservation_expires_at TIMESTAMP;")
            print("Added column: reservation_expires_at")
        except Exception as e:
            print(f"Error adding reservation_expires_at: {e}")

        # Add payment_method too while we are at it
        try:
            await conn.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS payment_method TEXT;")
            print("Added column: payment_method")
        except Exception as e:
            print(f"Error adding payment_method: {e}")

    print("Schema fix applied.")

if __name__ == "__main__":
    asyncio.run(apply_fix())
