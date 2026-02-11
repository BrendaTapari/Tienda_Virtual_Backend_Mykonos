#!/usr/bin/env python3
"""
Test script for waiting list filter functionality
"""
import asyncio
import sys
from config.db_connection import db

async def test_filters():
    print("=" * 60)
    print("WAITING LIST FILTER TESTING")
    print("=" * 60)
    
    # First, show current data
    print("\n1. Current Database State:")
    print("-" * 60)
    query = "SELECT id, producto_buscado, notificado FROM lista_espera ORDER BY id"
    rows = await db.fetch_all(query)
    
    notified_count = 0
    pending_count = 0
    
    for row in rows:
        status = "✓ NOTIFIED" if row["notificado"] else "○ PENDING"
        print(f"  {status} | ID: {row['id']:2d} | {row['producto_buscado']}")
        if row["notificado"]:
            notified_count += 1
        else:
            pending_count += 1
    
    total = len(rows)
    print(f"\nTotal: {total} | Notified: {notified_count} | Pending: {pending_count}")
    
    # Test filters
    print("\n2. Testing Filters:")
    print("-" * 60)
    
    # Test: no filter (all)
    query_all = """
        SELECT id, notificado FROM lista_espera
        ORDER BY id
    """
    all_results = await db.fetch_all(query_all)
    print(f"  No filter (all):     {len(all_results)} results (expected: {total})")
    
    # Test: pending only
    query_pending = """
        SELECT id, notificado FROM lista_espera
        WHERE notificado = $1
        ORDER BY id
    """
    pending_results = await db.fetch_all(query_pending, False)
    print(f"  Filter notificado=False: {len(pending_results)} results (expected: {pending_count})")
    
    # Test: notified only  
    notified_results = await db.fetch_all(query_pending, True)
    print(f"  Filter notificado=True:  {len(notified_results)} results (expected: {notified_count})")
    
    # Verify counts match
    print("\n3. Validation:")
    print("-" * 60)
    if len(all_results) == total:
        print("  ✓ Total count matches")
    else:
        print(f"  ✗ Total count mismatch: got {len(all_results)}, expected {total}")
    
    if len(pending_results) == pending_count:
        print("  ✓ Pending count matches")
    else:
        print(f"  ✗ Pending count mismatch: got {len(pending_results)}, expected {pending_count}")
    
    if len(notified_results) == notified_count:
        print("  ✓ Notified count matches")
    else:
        print(f"  ✗ Notified count mismatch: got {len(notified_results)}, expected {notified_count}")
    
    if len(pending_results) + len(notified_results) == total:
        print("  ✓ Pending + Notified = Total")
    else:
        print("  ✗ Sum doesn't match total")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_filters())
