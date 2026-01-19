
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def check_reservations():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    variant_id = 83 # From previous debug output for Pantalon L Naranja
    
    async with pool.acquire() as conn:
        print(f"Checking Active Reservations for Variant {variant_id}...")
        
        rows = await conn.fetch("""
            SELECT id, quantity, reserved_at, expires_at, status 
            FROM stock_reservations 
            WHERE variant_id = $1 AND status = 'active'
        """, variant_id)
        
        total_reserved = 0
        for r in rows:
            print(f"  Res ID {r['id']}: Qty {r['quantity']}, Expires {r['expires_at']}")
            total_reserved += r['quantity']
            
        print(f"Total Reserved: {total_reserved}")

        # Opt-in cleanup
        if total_reserved > 0:
            print("Cleaning up HEADLESS/TEST reservations...")
            await conn.execute("DELETE FROM stock_reservations WHERE variant_id = $1", variant_id)
            print("Reservations deleted.")

if __name__ == "__main__":
    asyncio.run(check_reservations())
