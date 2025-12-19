import asyncio
import os
from dotenv import load_dotenv
import asyncpg
from typing import Optional

# Load env vars
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mykonos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

class FakeDB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(**DB_CONFIG)

    async def fetch_all(self, query, values=None):
        if values is None:
            values = []
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *values)

db = FakeDB()

async def get_all_productos_logic(branch_id: Optional[int] = None):
    try:
        print(f"Testing with branch_id={branch_id}")
        
        # 1. Main Query
        if branch_id is None:
            print("--- MODO GLOBAL (WEB) ---")
            query_products = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) as images,
                    COALESCE(SUM(wv.displayed_stock), 0) as stock_disponible
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                LEFT JOIN web_variants wv ON wv.product_id = p.id AND wv.is_active = TRUE
                WHERE p.en_tienda_online = TRUE
                GROUP BY p.id, g.group_name
                ORDER BY p.id DESC
            """
            params_products = []
        else:
            print("--- MODO SUCURSAL ---")
            query_products = """
                SELECT 
                    p.id,
                    p.nombre_web,
                    p.descripcion_web,
                    p.precio_web,
                    p.slug,
                    COALESCE(g.group_name, 'Sin categoría') as category,
                    COALESCE(
                        ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) as images,
                    COALESCE(SUM(wsv.quantity), 0) as stock_disponible
                FROM products p
                LEFT JOIN groups g ON p.group_id = g.id
                LEFT JOIN images i ON i.product_id = p.id
                JOIN web_variants wv ON wv.product_id = p.id 
                LEFT JOIN warehouse_stock_variants wsv 
                    ON wsv.product_id = p.id 
                    AND wsv.size_id = wv.size_id 
                    AND wsv.color_id = wv.color_id
                    AND wsv.branch_id = $1 
                WHERE p.en_tienda_online = TRUE AND wv.is_active = TRUE
                GROUP BY p.id, g.group_name
                ORDER BY p.id DESC
            """
            params_products = [branch_id]

        print("Executing product query...")
        products = await db.fetch_all(query_products, values=params_products)
        print(f"Found {len(products)} products.")

        # 2. Variants
        result = []
        for product in products:
            product_dict = dict(product)
            print(f"Processing product: {product['id']}")
            
            if branch_id is None:
                variants_query = """
                    SELECT 
                        wv.id as web_variant_id,
                        s.size_name as talle,
                        c.color_name as color,
                        c.color_hex,
                        wv.displayed_stock as stock,
                        '' as barcode
                    FROM web_variants wv
                    LEFT JOIN sizes s ON wv.size_id = s.id
                    LEFT JOIN colors c ON wv.color_id = c.id
                    WHERE wv.product_id = $1 AND wv.is_active = TRUE
                    ORDER BY s.size_name, c.color_name
                """
                variants = await db.fetch_all(variants_query, values=[product['id']])
            else:
                variants_query = """
                    SELECT 
                        wv.id as web_variant_id,
                        s.size_name as talle,
                        c.color_name as color,
                        c.color_hex,
                        COALESCE(wsv.quantity, 0) as stock,
                        wsv.variant_barcode as barcode
                    FROM web_variants wv
                    LEFT JOIN sizes s ON wv.size_id = s.id
                    LEFT JOIN colors c ON wv.color_id = c.id
                    LEFT JOIN warehouse_stock_variants wsv 
                        ON wsv.product_id = wv.product_id 
                        AND wsv.size_id = wv.size_id 
                        AND wsv.color_id = wv.color_id
                        AND wsv.branch_id = $2
                    WHERE wv.product_id = $1 AND wv.is_active = TRUE
                    ORDER BY s.size_name, c.color_name
                """
                variants = await db.fetch_all(variants_query, values=[product['id'], branch_id])

            product_dict['variantes'] = [
                {
                    "variant_id": v['web_variant_id'],
                    "talle": v['talle'],
                    "color": v['color'],
                    "color_hex": v['color_hex'],
                    "stock": v['stock'],
                    "barcode": v['barcode'] if v['barcode'] else "WEB-VAR"
                } 
                for v in variants
            ]
            
            result.append(product_dict)
        
        print(f"Successfully processed {len(result)} products.")
        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await db.connect()
    # verify if there are any products online
    try:
         print("Checking if any products have en_tienda_online=TRUE...")
         count = await db.fetch_all("SELECT COUNT(*) FROM products WHERE en_tienda_online = TRUE")
         print(f"Products online: {count[0]['count']}")
         
         print("Checking web_variants count...")
         count = await db.fetch_all("SELECT COUNT(*) FROM web_variants")
         print(f"Web variants: {count[0]['count']}")
    except Exception as e:
        print(f"Error checking counts: {e}")

    await get_all_productos_logic(None)

if __name__ == "__main__":
    asyncio.run(main())
