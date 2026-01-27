
import asyncio
import sys
import logging
from config.db_connection import DatabaseManager

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_users():
    await DatabaseManager.initialize()
    pool = await DatabaseManager.get_pool()

    patterns = [
        'SimulatedUser%',
        'forgot_%',
        'user_%',
        'admin_test_%',
        'checkout_test_%'
    ]

    async with pool.acquire() as conn:
        all_users = []
        for pattern in patterns:
            users = await conn.fetch("SELECT id, username FROM web_users WHERE username LIKE $1", pattern)
            all_users.extend(users)

        # Remove duplicates
        unique_users = {u['id']: u for u in all_users}.values()
        user_ids = [u['id'] for u in unique_users]
        
        if not user_ids:
            logger.info("No users found to delete.")
            return

        logger.info(f"Found {len(user_ids)} users to delete.")
        
        # 1. Get related Sales (Orders)
        sales = await conn.fetch("SELECT id FROM sales WHERE web_user_id = ANY($1::int[])", user_ids)
        sale_ids = [s['id'] for s in sales]
        
        logger.info(f"Found {len(sale_ids)} related orders.")

        async with conn.transaction():
            # Delete Sales related data
            if sale_ids:
                # Tracking History
                res = await conn.execute("DELETE FROM sales_tracking_history WHERE sale_id = ANY($1::int[])", sale_ids)
                logger.info(f"Deleted tracking history: {res}")

                # Stock Reservations
                res = await conn.execute("DELETE FROM stock_reservations WHERE sale_id = ANY($1::int[])", sale_ids)
                logger.info(f"Deleted stock reservations: {res}")

                # Sales Details (Order Items)
                res = await conn.execute("DELETE FROM sales_detail WHERE sale_id = ANY($1::int[])", sale_ids)
                logger.info(f"Deleted sales details: {res}")

                # Sales
                res = await conn.execute("DELETE FROM sales WHERE id = ANY($1::int[])", sale_ids)
                logger.info(f"Deleted sales: {res}")

            # Delete Cart related data
            # Get carts
            carts = await conn.fetch("SELECT id FROM web_carts WHERE user_id = ANY($1::int[])", user_ids)
            cart_ids = [c['id'] for c in carts]
            
            if cart_ids:
                # Cart Items
                res = await conn.execute("DELETE FROM web_cart_items WHERE cart_id = ANY($1::int[])", cart_ids)
                logger.info(f"Deleted cart items: {res}")
                
                # Carts
                res = await conn.execute("DELETE FROM web_carts WHERE id = ANY($1::int[])", cart_ids)
                logger.info(f"Deleted carts: {res}")

            # Delete Users
            res = await conn.execute("DELETE FROM web_users WHERE id = ANY($1::int[])", user_ids)
            logger.info(f"Deleted users: {res}")
            
        logger.info("Cleanup completed successfully.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(cleanup_users())
