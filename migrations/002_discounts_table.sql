-- Migration: Create discounts table for group discount management
-- Date: 2025-12-12

BEGIN;

-- Create discounts table
CREATE TABLE IF NOT EXISTS discounts (
    id SERIAL PRIMARY KEY,
    discount_type TEXT NOT NULL CHECK (discount_type IN ('group', 'product', 'category')),
    target_id INTEGER,  -- group_id or product_id depending on type
    target_name TEXT,
    discount_percentage NUMERIC(5,2) NOT NULL CHECK (discount_percentage > 0 AND discount_percentage < 100),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    apply_to_children BOOLEAN DEFAULT FALSE,  -- For group discounts: apply to subgroups
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to users table (who created the discount)
    CONSTRAINT fk_discount_creator FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_discounts_type_target ON discounts(discount_type, target_id);
CREATE INDEX IF NOT EXISTS idx_discounts_active ON discounts(is_active);
CREATE INDEX IF NOT EXISTS idx_discounts_dates ON discounts(start_date, end_date);

COMMIT;
