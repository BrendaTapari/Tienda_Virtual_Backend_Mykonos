
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def debug_cart():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        print("Fetching most recent cart items...")
        
        # Get latest cart
        cart_id = await conn.fetchval("SELECT id FROM web_carts ORDER BY created_at DESC LIMIT 1")
        print(f"Latest Cart ID: {cart_id}")
        
        if not cart_id: return

        items = await conn.fetch("""
            SELECT wci.id, wci.product_id, wci.variant_id, wci.quantity,
                   p.nombre_web, p.precio_web
            FROM web_cart_items wci
            JOIN products p ON wci.product_id = p.id
            WHERE wci.cart_id = $1
        """, cart_id)
        
        for item in items:
            print(f"Item {item['id']}: Product {item['product_id']} ({item['nombre_web']}) - Variant {item['variant_id']} - Qty {item['quantity']}")
            
            # Check what this variant ID corresponds to
            wv = await conn.fetchrow("SELECT * FROM web_variants WHERE id=$1", item['variant_id'])
            if wv:
                print(f"  -> Matches Web Variant {wv['id']} (Size {wv['size_id']}, Color {wv['color_id']})")
                
            wsv = await conn.fetchrow("SELECT * FROM warehouse_stock_variants WHERE id=$1", item['variant_id'])
            if wsv:
                 print(f"  -> Matches Warehouse Variant {wsv['id']} (Size {wsv['size_id']}, Color {wsv['color_id']})")

            # Run the stock query specifically for this variant
            stock_avail = await conn.fetchval("""
                SELECT SUM(cantidad_asignada)
                FROM web_variant_branch_assignment
                WHERE variant_id = $1
            """, item['variant_id'])
            print(f"  -> Stock Query (Direct) Result: {stock_avail}")


if __name__ == "__main__":
    asyncio.run(debug_cart())
