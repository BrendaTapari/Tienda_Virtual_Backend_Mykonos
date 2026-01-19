
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.db_connection import DatabaseManager

async def check_variants_and_discounts():
    print("=== CHECKING VARIANTS AND DISCOUNTS ===")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # 1. web_variants for Product 3
        print("\n--- Web Variants (Product 3) ---")
        wvs = await conn.fetch("SELECT * FROM web_variants WHERE product_id = 3")
        for wv in wvs:
            print(dict(wv))
            
        # 2. discounts table
        print("\n--- Active Discounts ---")
        discounts = await conn.fetch("SELECT * FROM discounts WHERE is_active = TRUE")
        for d in discounts:
            print(dict(d))

        # 3. products table for Product 3
        print("\n--- Product 3 Data ---")
        p = await conn.fetchrow("SELECT id, has_discount, discount_percentage, precio_web FROM products WHERE id = 3")
        print(dict(p))

if __name__ == "__main__":
    asyncio.run(check_variants_and_discounts())
