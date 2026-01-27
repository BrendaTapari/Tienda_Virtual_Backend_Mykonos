#!/usr/bin/env python3
"""
Script to delete user brenda.tapari from the database.
This will delete the user and all associated data (cart, cart items, etc.)
"""

import asyncio
import sys
sys.path.append('/home/breightend/Tienda_Virtual_Backend_Mykonos')

from config.db_connection import db

async def delete_user():
    """Delete user brendatapa6 and all associated data"""
    
    username = "brendatapa6"
    
    try:
        # Check if user exists
        user = await db.fetch_one(
            "SELECT id, username, email FROM web_users WHERE username = $1",
            username
        )
        
        if not user:
            print(f"❌ User '{username}' not found in database")
            return
        
        print(f"✓ Found user: {user['username']} (ID: {user['id']}, Email: {user['email']})")
        print(f"\n🗑️  Deleting user and all associated data...\n")
        
        user_id = user['id']
        
        # 1. Delete cart items first (foreign key constraint)
        cart_items_deleted = await db.execute(
            """
            DELETE FROM web_cart_items 
            WHERE cart_id IN (SELECT id FROM web_carts WHERE user_id = $1)
            """,
            user_id
        )
        print(f"  ✓ Deleted cart items: {cart_items_deleted}")
        
        # 2. Delete cart
        cart_deleted = await db.execute(
            "DELETE FROM web_carts WHERE user_id = $1",
            user_id
        )
        print(f"  ✓ Deleted cart: {cart_deleted}")
        
        # 3. Delete user
        user_deleted = await db.execute(
            "DELETE FROM web_users WHERE id = $1",
            user_id
        )
        print(f"  ✓ Deleted user: {user_deleted}")
        
        print(f"\n✅ User '{username}' and all associated data deleted successfully!")
        print(f"   You can now create this user again.\n")
        
    except Exception as e:
        print(f"\n❌ Error deleting user: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(delete_user())
