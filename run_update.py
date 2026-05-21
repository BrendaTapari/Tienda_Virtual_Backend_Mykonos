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
    
    result = await conn.execute("""
        UPDATE warehouse_stock_variants 
        SET variant_barcode = '20' || LPAD(product_id::text, 4, '0') || LPAD(size_id::text, 3, '0') || LPAD(color_id::text, 3, '0')
        WHERE length(variant_barcode) = 14 AND variant_barcode LIKE '0%';
    """)
    print(f"Update result: {result}")
    
    await conn.close()

asyncio.run(main())
