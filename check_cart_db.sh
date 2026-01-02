#!/bin/bash

echo "=== CHECKING CART ITEMS FOR CART_ID 2 ==="
echo ""

# Connect to database and run queries
export PGPASSWORD="${DB_PASSWORD:-mykonos2024}"

psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-mykonos_user}" -d "${DB_NAME:-mykonos_db}" << 'EOF'

-- Check cart items
SELECT 
    wci.id as cart_item_id,
    wci.product_id,
    wci.variant_id,
    wci.quantity as cart_quantity,
    p.nombre_web as product_name
FROM web_cart_items wci
JOIN products p ON wci.product_id = p.id
WHERE wci.cart_id = 2
ORDER BY wci.id;

\echo ''
\echo '=== CHECKING VARIANT DETAILS ==='
\echo ''

-- For each variant in cart, check if it's in web_variants or warehouse_stock_variants
SELECT 
    wci.id as cart_item_id,
    wci.variant_id,
    CASE 
        WHEN wv.id IS NOT NULL THEN 'web_variants'
        WHEN wsv.id IS NOT NULL THEN 'warehouse_stock_variants'
        ELSE 'NOT FOUND'
    END as variant_table
FROM web_cart_items wci
LEFT JOIN web_variants wv ON wci.variant_id = wv.id
LEFT JOIN warehouse_stock_variants wsv ON wci.variant_id = wsv.id
WHERE wci.cart_id = 2;

\echo ''
\echo '=== WEB STOCK ASSIGNMENTS FOR CART VARIANTS ==='
\echo ''

-- Check web stock for variants in cart
SELECT 
    wci.id as cart_item_id,
    wci.variant_id,
    wvba.branch_id,
    wvba.cantidad_asignada as web_stock,
    (SELECT SUM(cantidad_asignada) FROM web_variant_branch_assignment WHERE variant_id = wci.variant_id) as total_web_stock
FROM web_cart_items wci
LEFT JOIN web_variant_branch_assignment wvba ON wci.variant_id = wvba.variant_id
WHERE wci.cart_id = 2
ORDER BY wci.id, wvba.branch_id;

\echo ''
\echo '=== PRODUCT 6 WEB VARIANTS AND STOCK ==='
\echo ''

-- Check all web variants for product 6
SELECT 
    wv.id as variant_id,
    s.size_name,
    c.color_name,
    wvba.branch_id,
    wvba.cantidad_asignada as web_stock
FROM web_variants wv
LEFT JOIN sizes s ON wv.size_id = s.id
LEFT JOIN colors c ON wv.color_id = c.id
LEFT JOIN web_variant_branch_assignment wvba ON wv.id = wvba.variant_id
WHERE wv.product_id = 6
ORDER BY wv.id, wvba.branch_id;

EOF
