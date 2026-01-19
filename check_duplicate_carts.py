import asyncio
import os
import sys

sys.path.append(os.getcwd())
from config.db_connection import DatabaseManager, db

async def check_duplicates():
    await DatabaseManager.initialize()
    try:
        query = """
        SELECT user_id, count(*) 
        FROM web_carts 
        GROUP BY user_id 
        HAVING count(*) > 1
        """
        rows = await db.fetch_all(query)
        if rows:
            print("DUPLICATE CARTS FOUND:")
            for row in rows:
                print(f"User ID: {row['user_id']}, Count: {row['count']}")
        else:
            print("No duplicate carts found (1 cart per user constraints likely active or respected).")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(check_duplicates())
