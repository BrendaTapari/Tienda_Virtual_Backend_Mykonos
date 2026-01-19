
import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

async def debug_stock():
    print("Connecting to DB...")
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        print("Searching for product 'Pantalon'...")
        
        # 1. Find Product
        products = await conn.fetch("SELECT id, nombre_web, provider_code FROM products WHERE nombre_web LIKE '%Pantalon%'")
        if not products:
            print("No matching products found.")
            return

        for p in products:
            print(f"\nProduct: ID {p['id']} - {p['nombre_web']}")
            
            # 2. Check Web Variants and Assignments
            print("  --- Web Variants & Assignments ---")
            web_vars = await conn.fetch("""
                SELECT wv.id, wv.size_id, wv.color_id, s.size_name, c.color_name,
                       COALESCE((SELECT SUM(cantidad_asignada) FROM web_variant_branch_assignment WHERE variant_id=wv.id), 0) as total_assigned
                FROM web_variants wv
                JOIN sizes s ON wv.size_id = s.id
                JOIN colors c ON wv.color_id = c.id
                WHERE wv.product_id = $1
            """, p['id'])
            
            for wv in web_vars:
                print(f"    WebVar ID {wv['id']} ({wv['size_name']}, {wv['color_name']}): Assigned Stock = {wv['total_assigned']}")

            # 3. Check Warehouse Stock Variants (The physical stock)
            print("  --- Warehouse Stock Variants (Physical) ---")
            warehouse_vars = await conn.fetch("""
                SELECT wsv.id, wsv.size_id, wsv.color_id, s.size_name, c.color_name, wsv.quantity
                FROM warehouse_stock_variants wsv
                JOIN sizes s ON wsv.size_id = s.id
                JOIN colors c ON wsv.color_id = c.id
                WHERE wsv.product_id = $1
            """, p['id'])
            
            for wsv in warehouse_vars:
                 print(f"    WarehouseVar ID {wsv['id']} ({wsv['size_name']}, {wsv['color_name']}): Quantity = {wsv['quantity']}")

if __name__ == "__main__":
    asyncio.run(debug_stock())
