import asyncio
import asyncpg

async def fix_order():
    conn = await asyncpg.connect(user="breightend_db", password="ñmICHIFUS156602", database="mykonos_db", host="localhost")
    # Update sales_detail
    await conn.execute("""
        UPDATE sales_detail
        SET discount_percentage = 2.00,
            discount_amount = 0.15,
            sale_price = 7.35,
            subtotal = 7.35,
            total = 7.35
        WHERE sale_id = 215 AND product_id = 577
    """)
    # Update sales
    await conn.execute("""
        UPDATE sales
        SET subtotal = 7.35,
            total = 7.35,
            discount = 0.15
        WHERE id = 215
    """)
    print("Fixed order 215")
    await conn.close()

asyncio.run(fix_order())
