import asyncio
import os
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

# Load env vars
load_dotenv()

async def r():
    try:
        print("Initializing DB...")
        await DatabaseManager.initialize()
        
        migration_file = "migrations/007_add_notifications.sql"
        print(f"Reading migration file: {migration_file}")
        
        with open(migration_file, "r") as f:
            sql_content = f.read()
            
        print("Executing migration...")
        # Split by semicolon if multiple statements needed, usually execute can handle blocks
        # asyncpg execute might handle multiple statements if passed as block?
        # Let's try executing the whole block.
        await DatabaseManager.execute(sql_content)
        
        print("Migration executed successfully!")
        
    except Exception as e:
        print(f"Error running migration: {e}")
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(r())
