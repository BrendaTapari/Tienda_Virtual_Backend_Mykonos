import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'breightend_db'),
        password=os.getenv('DB_PASSWORD', 'ñmICHIFUS156602'),
        database=os.getenv('DB_NAME', 'mykonos_db')
    )
    
    rows = await conn.fetch("SELECT id, product_id, size_id, color_id FROM warehouse_stock_variants WHERE length(variant_barcode) = 14 AND variant_barcode LIKE '0%' AND size_id IS NULL;")
    print(f"Old format with null size_id: {len(rows)}")

    rows2 = await conn.fetch("SELECT id, product_id, size_id, color_id FROM warehouse_stock_variants WHERE length(variant_barcode) = 14 AND variant_barcode LIKE '0%' AND color_id IS NULL;")
    print(f"Old format with null color_id: {len(rows2)}")
    
    await conn.close()

asyncio.run(main())
