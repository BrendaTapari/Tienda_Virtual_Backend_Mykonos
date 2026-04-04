import asyncio
import os
import re
import sys
from pathlib import Path
from config.db_connection import DatabaseManager
from dotenv import load_dotenv

# Load env vars
load_dotenv()


def _latest_migration_file(migrations_dir: Path) -> Path:
    sql_files = list(migrations_dir.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"No .sql migration files found in {migrations_dir}")

    def migration_key(path: Path):
        # Supports names like 019_coupon_deactivated_at.sql
        match = re.match(r"^(\d+)_", path.name)
        prefix = int(match.group(1)) if match else -1
        return (prefix, path.name)

    return sorted(sql_files, key=migration_key)[-1]


def _resolve_migration_file() -> str:
    migrations_dir = Path("migrations")

    # Optional usage: python3 run_migration.py migrations/018_coupons.sql
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if not candidate.exists():
            raise FileNotFoundError(f"Migration file not found: {candidate}")
        return str(candidate)

    latest = _latest_migration_file(migrations_dir)
    return str(latest)


async def r():
    try:
        print("Initializing DB...")
        await DatabaseManager.initialize()

        migration_file = _resolve_migration_file()
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
