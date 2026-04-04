import asyncio
from config.db_connection import DatabaseManager

async def run():
    await DatabaseManager.initialize()
    with open("migrations/018_coupons.sql", "r") as f:
        sql = f.read()
    await DatabaseManager.execute(sql)
    await DatabaseManager.close()
    print("Migration 018 completed successfully")

if __name__ == "__main__":
    asyncio.run(run())
