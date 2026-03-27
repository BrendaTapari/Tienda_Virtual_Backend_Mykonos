import asyncio
from config.db_connection import DatabaseManager

async def run():
    await DatabaseManager.initialize()
    with open("migrations/015_shipping_config.sql", "r") as f:
        sql = f.read()
    await DatabaseManager.execute(sql)
    await DatabaseManager.close()
    print("Migration 015 completed successfully")

if __name__ == "__main__":
    asyncio.run(run())
