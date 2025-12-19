BEGIN;

-- ---------------------------------------------------------
-- 1. CREACIÓN DE LA TABLA WEB_VARIANTS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS web_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    size_id INTEGER NOT NULL,
    color_id INTEGER NOT NULL,
    displayed_stock INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_web_variants_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_web_variants_size FOREIGN KEY (size_id) REFERENCES sizes(id),
    CONSTRAINT fk_web_variants_color FOREIGN KEY (color_id) REFERENCES colors(id),
    -- Constraint para evitar duplicados de variantes en la web
    CONSTRAINT uq_web_variants UNIQUE (product_id, size_id, color_id)
);

-- ---------------------------------------------------------
-- 2. ACTUALIZACIÓN DE LA TABLA WEB_CART_ITEMS
-- ---------------------------------------------------------

-- Eliminamos la foreign key anterior que apuntaba a warehouse_stock_variants
ALTER TABLE web_cart_items DROP CONSTRAINT IF EXISTS fk_cart_items_variant;

-- Limpiamos datos existentes que darían error de FK al no existir en web_variants
TRUNCATE TABLE web_cart_items RESTART IDENTITY CASCADE;

-- Agregamos la nueva foreign key que apunta a web_variants
ALTER TABLE web_cart_items 
    ADD CONSTRAINT fk_cart_items_web_variant 
    FOREIGN KEY (variant_id) REFERENCES web_variants(id);

COMMIT;
