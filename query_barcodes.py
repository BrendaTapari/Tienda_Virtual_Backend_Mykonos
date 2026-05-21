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
    
    rows = await conn.fetch("SELECT id, variant_barcode, size_id, color_id FROM warehouse_stock_variants WHERE product_id = 577;")
    for row in rows:
        print(dict(row))
        
    await conn.close()

asyncio.run(main())
