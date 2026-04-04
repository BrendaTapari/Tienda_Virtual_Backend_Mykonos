import asyncio
from config.db_connection import DatabaseManager, db

async def migrate():
    await DatabaseManager.initialize()
    try:
        # Clear existing coupons and rules completely to avoid type conflicts with the ALTER
        print("Limpiando tablas de cupones actuales...")
        await db.execute("DELETE FROM coupons")
        await db.execute("DELETE FROM coupon_types")

        print("Actualizando esquema de DB:")
        # Modificar coupon_types para quitar discount_value
        print(">> ALTER TABLE coupon_types DROP COLUMN IF EXISTS discount_value")
        await db.execute("ALTER TABLE coupon_types DROP COLUMN IF EXISTS discount_value")

        # Modificar coupons para agregar discount_value
        print(">> ALTER TABLE coupons ADD COLUMN discount_value NUMERIC(10, 2) DEFAULT 0")
        try:
            # En SQLite/Postgres podría fallar si ya existe, probamos atraparlo suave
            await db.execute("ALTER TABLE coupons ADD COLUMN discount_value NUMERIC(10, 2) DEFAULT 0")
        except Exception as add_e:
            if "already exists" not in str(add_e).lower() and "column discount_value" not in str(add_e).lower():
                raise add_e
            else:
                print("La columna discount_value ya existe en coupons, prosiguiendo.")

        print("✅ Migración de esquema (ALTER) completada exitosamente.")
    except Exception as e:
        print(f"❌ Error migrando el esquema: {e}")
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(migrate())
