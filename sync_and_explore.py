
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.db_connection import DatabaseManager

async def sync_discounts_and_explore():
    print("=== SYNCING DATA & EXPLORING BRANCHES ===")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # 1. Sync Discounts
        print("\nSyncing Products with Active Discounts...")
        # Get active discounts
        discounts = await conn.fetch("SELECT * FROM discounts WHERE is_active = TRUE AND discount_type = 'product'")
        
        for d in discounts:
            print(f"Applying Discount ID {d['id']} (3%) to Product {d['target_id']}...")
            
            # Get product original price
            p = await conn.fetchrow("SELECT id, precio_web FROM products WHERE id = $1", d['target_id'])
            if not p:
                continue
                
            original_price = float(p['precio_web'])
            discount_pct = float(d['discount_percentage'])
            discount_amount = original_price * (discount_pct / 100.0)
            sale_price = original_price - discount_amount
            
            await conn.execute("""
                UPDATE products 
                SET has_discount = 1,
                    discount_percentage = $1,
                    discount_amount = $2,
                    sale_price = $3,
                    original_price = precio_web -- Ensure original is set
                WHERE id = $4
            """, d['discount_percentage'], discount_amount, sale_price, p['id'])
            print(f" -> Updated Product {p['id']}: web=${original_price} -> sale=${sale_price}")

        # 2. Explore Branches
        print("\n--- Branches ---")
        try:
            branches = await conn.fetch("SELECT * FROM branches")
            for b in branches:
                print(dict(b))
        except Exception as e:
            print(f"Error fetching branches: {e}")
            
        # Check sales detail for potential duplicates in recent sales
        print("\n--- Checking recent sales details for duplication ---")
        # Look for sales where same product appears multiple times
        dupes = await conn.fetch("""
            SELECT sale_id, product_id, COUNT(*) 
            FROM sales_detail 
            GROUP BY sale_id, product_id 
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        for d in dupes:
            print(f"Sale {d['sale_id']} has duplicate Product {d['product_id']} (Count: {d['count']})")


if __name__ == "__main__":
    asyncio.run(sync_discounts_and_explore())
