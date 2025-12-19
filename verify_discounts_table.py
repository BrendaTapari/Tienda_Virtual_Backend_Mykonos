#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mykonos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

async def verify_discounts():
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'discounts')"
        )
        await conn.close()
        
        if exists:
            print("YES: The 'discounts' table EXISTS in the database.")
        else:
            print("NO: The 'discounts' table does NOT exist in the database.")
            
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    asyncio.run(verify_discounts())
