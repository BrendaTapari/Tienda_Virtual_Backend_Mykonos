import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from config.db_connection import db

async def verify():
    print("Initializing database connection...")
    try:
        await db.initialize()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    print("Connected.")

    # 1. Apply Migration locally for verification
    print("Reading migration file...")
    try:
        with open("migrations/012_update_branch_schema.sql", "r") as f:
            migration_sql = f.read()
        
        print("Applying migration (ignoring errors if columns already exist)...")
        # Split into statements because asyncpg might execute one by one or all.
        # usually execute takes one statement, or use execute multiple times.
        # But simple script: split by ;
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        for stmt in statements:
            try:
                await db.execute(stmt)
                print(f"Executed: {stmt[:50]}...")
            except Exception as e:
                print(f"Migration step failed (might be already applied): {e}")
    except Exception as e:
        print(f"Error checking/applying migration: {e}")

    # 2. Verify Schema
    print("\nChecking 'storage' table columns...")
    try:
        # Postgres way to check columns
        rows = await db.fetch_all("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'storage'
        """)
        columns = [row['column_name'] for row in rows]
        print(f"Columns: {columns}")
        
        required = ['sucursal', 'direccion', 'telefono', 'maps_link', 'horarios', 'instagram']
        missing = [c for c in required if c not in columns]
        
        if missing:
            print(f"FAILED: Missing columns: {missing}")
        else:
            print("SUCCESS: All required columns present.")
            
    except Exception as e:
        print(f"Error checking schema: {e}")

    # 3. Verify Insert/Select
    print("\nChecking CRUD operations...")
    try:
        # Insert
        query_insert = """
            INSERT INTO storage (sucursal, direccion, maps_link, horarios, telefono, instagram)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """
        vals = ("Test Branch", "123 Test St", "http://maps", "9-5", "123456", "@test")
        
        branch_id = await db.fetch_val(query_insert, *vals)
        print(f"SUCCESS: Inserted branch ID: {branch_id}")
        
        # Select
        row = await db.fetch_one("SELECT * FROM storage WHERE id = $1", branch_id)
        if row:
            print(f"SUCCESS: Fetched branch: {row['sucursal']}, {row['instagram']}")
            
            # Update (Test renaming/new cols usage)
            await db.execute("UPDATE storage SET instagram = '@updated' WHERE id = $1", branch_id)
            updated = await db.fetch_val("SELECT instagram FROM storage WHERE id = $1", branch_id)
            if updated == '@updated':
                print("SUCCESS: Updated branch instagram.")
            else:
                print(f"FAILED: Update failed. Got {updated}")
            
            # Delete
            await db.execute("DELETE FROM storage WHERE id = $1", branch_id)
            print("SUCCESS: Deleted test branch.")
        else:
            print("FAILED: Could not fetch inserted branch.")
            
    except Exception as e:
        print(f"FAILED: CRUD error: {e}")

    await db.close()

if __name__ == "__main__":
    asyncio.run(verify())
