-- Migration 016: Add web tags tables and new product columns
-- Date: 2026-03-28

-- Add new columns to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS alt_text TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS technical_details TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS base_description TEXT;

-- Create web_tags table
CREATE TABLE IF NOT EXISTS web_tags (
    id         SERIAL PRIMARY KEY,
    tag_name   TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create product_tags join table (many-to-many: products <-> web_tags)
CREATE TABLE IF NOT EXISTS product_tags (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES web_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, tag_id)
);
