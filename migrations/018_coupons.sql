-- Migration XXX: Create coupon_types and coupons tables for the new discount system
-- Implements a 2-table template architecture and links optionally to web_users.

-- 1. Create the Coupon Types table (The Business Rules)
CREATE TABLE IF NOT EXISTS coupon_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    discount_type VARCHAR(50) NOT NULL, -- e.g., 'percentage', 'fixed_amount', 'free_shipping'
    discount_value NUMERIC(10, 2) DEFAULT 0
);

-- 2. Create the Coupons table (The Instances)
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    type_id INTEGER NOT NULL,
    user_id INTEGER, -- NULL means it's a global coupon
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    usage_limit INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    -- Foreign Key to coupon_types
    -- RESTRICT prevents deleting a type if coupons are still using it
    CONSTRAINT fk_coupon_type 
        FOREIGN KEY (type_id) 
        REFERENCES coupon_types (id) 
        ON DELETE RESTRICT,

    -- Foreign Key to web_users
    -- SET NULL means if the user is deleted, the coupon becomes global/unassigned instead of breaking
    CONSTRAINT fk_coupon_user 
        FOREIGN KEY (user_id) 
        REFERENCES web_users (id) 
        ON DELETE SET NULL
);

-- 3. Create indexes for faster queries during checkout
-- Index the code since we will search by it constantly when a user applies a coupon
CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons (code);

-- Index the user_id to quickly find all coupons assigned to a specific user
CREATE INDEX IF NOT EXISTS idx_coupons_user_id ON coupons (user_id);