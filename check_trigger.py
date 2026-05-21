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
    
    triggers = await conn.fetch("SELECT event_object_table, trigger_name, action_statement FROM information_schema.triggers WHERE event_object_table = 'warehouse_stock_variants';")
    for t in triggers:
        print(dict(t))
        
    await conn.close()

asyncio.run(main())
