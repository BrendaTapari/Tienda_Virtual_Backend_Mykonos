
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.db_connection import DatabaseManager

async def check_branch_schema():
    print("=== BRANCH SCHEMA INSPECTION ===")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Check assignments to get column names
        print("\n--- Web Variant Branch Assignment (Sample) ---")
        assign = await conn.fetchrow("SELECT * FROM web_variant_branch_assignment LIMIT 1")
        if assign:
            print(dict(assign))
            # Try to query the table referenced by branch_id
            # Assuming 'sucursales' based on common Spanish naming if 'branches' failed
            # Or inspect tables in information_schema
            
            print("\n--- Inspecting Tables ---")
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%branch%' OR table_name LIKE '%sucur%' OR table_name LIKE '%stock%'
            """)
            print([t['table_name'] for t in tables])

if __name__ == "__main__":
    asyncio.run(check_branch_schema())
