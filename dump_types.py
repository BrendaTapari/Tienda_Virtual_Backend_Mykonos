import asyncio
from config.db_connection import DatabaseManager, db

async def run():
    await DatabaseManager.initialize()
    rows = await db.fetch_all("SELECT * FROM coupon_types")
    print("TIPOS EN BASE DE DATOS:")
    for r in rows:
        print(dict(r))
    await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(run())
