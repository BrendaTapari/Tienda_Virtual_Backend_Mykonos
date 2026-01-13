
import asyncio
import os
from dotenv import load_dotenv
from config.db_connection import DatabaseManager

load_dotenv()

async def main():
    try:
        await DatabaseManager.initialize()
        user = await DatabaseManager.fetch_one(
            "SELECT session_token FROM web_users WHERE role='admin' LIMIT 1"
        )
        if user:
            print(user['session_token'])
        else:
            print("NO_ADMIN_FOUND")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(main())
