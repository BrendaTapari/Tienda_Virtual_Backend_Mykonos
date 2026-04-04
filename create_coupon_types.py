import asyncio
from config.db_connection import DatabaseManager, db

async def setup_coupon_types():
    print("Iniciando conexión a la base de datos...")
    await DatabaseManager.initialize()
    
    # 3 STANDARDIZED TEMPLATES ONLY
    standard_rules = [
        {
            "name": "Porcentaje (%)",
            "discount_type": "percentage"
        },
        {
            "name": "Monto Fijo ($)",
            "discount_type": "fixed_amount"
        },
        {
            "name": "Envío Gratis",
            "discount_type": "free_shipping"
        }
    ]

    print(f"Insertando las {len(standard_rules)} reglas de negocio universales estandarizadas...")
    
    query = """
        INSERT INTO coupon_types (name, discount_type)
        VALUES ($1, $2)
        RETURNING id;
    """

    try:
        inserted_count = 0
        for rule in standard_rules:
            existing = await db.fetch_one("SELECT id FROM coupon_types WHERE discount_type = $1", rule["discount_type"])
            if not existing:
                row = await db.fetch_one(query, rule["name"], rule["discount_type"])
                print(f"✅ Regla creada -> ID: {row['id']} | Nombre: {rule['name']}")
                inserted_count += 1
            else:
                print(f"⚠️ La regla tipo '{rule['discount_type']}' ya existía. Saltando...")
        
        print(f"\n🎉 Terminado. Se estandarizaron {inserted_count} reglas universales.")
    except Exception as e:
        print(f"❌ Ocurrió un error al intentar crear los tipos estandar: {e}")
    finally:
        await DatabaseManager.close()
        print("Conexión cerrada.")

if __name__ == "__main__":
    asyncio.run(setup_coupon_types())
