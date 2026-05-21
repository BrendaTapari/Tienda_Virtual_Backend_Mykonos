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
    
    # Check how many have the old 14-digit format starting with 0
    count = await conn.fetchval("SELECT count(*) FROM warehouse_stock_variants WHERE length(variant_barcode) = 14 AND variant_barcode LIKE '0%';")
    print(f"Old format barcodes: {count}")
    
    await conn.close()

asyncio.run(main())
