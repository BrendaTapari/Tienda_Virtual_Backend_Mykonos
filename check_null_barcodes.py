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
    
    count_null = await conn.fetchval("SELECT count(*) FROM warehouse_stock_variants WHERE variant_barcode IS NULL OR variant_barcode = '';")
    print(f"Null/Empty barcodes: {count_null}")
    
    await conn.close()

asyncio.run(main())
