-- Migration 017: Make web_variants.size_id nullable (for products without sizes, e.g. jewellery)
-- Also recreates the UNIQUE constraint to handle NULL size_id correctly.

-- 1. Drop the old NOT NULL constraint by altering the column
ALTER TABLE web_variants ALTER COLUMN size_id DROP NOT NULL;

-- 2. Drop the existing UNIQUE constraint (name may vary; try both common names)
ALTER TABLE web_variants DROP CONSTRAINT IF EXISTS web_variants_product_id_size_id_color_id_key;
ALTER TABLE web_variants DROP CONSTRAINT IF EXISTS unique_product_size_color;

-- 3. Re-create a partial unique index that handles NULLs correctly:
--    Two NULLs are never equal in SQL, so we split into two partial indexes.
--    Index A: when size_id IS NOT NULL
CREATE UNIQUE INDEX IF NOT EXISTS uq_web_variants_with_size
    ON web_variants (product_id, size_id, color_id)
    WHERE size_id IS NOT NULL;

--    Index B: when size_id IS NULL (only one entry per product+color allowed)
CREATE UNIQUE INDEX IF NOT EXISTS uq_web_variants_no_size
    ON web_variants (product_id, color_id)
    WHERE size_id IS NULL;
