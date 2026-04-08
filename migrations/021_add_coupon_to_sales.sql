-- Migration 021: Add coupon tracking fields to the sales table
-- These columns record the coupon data at the moment of purchase (historical snapshot),
-- allowing reports to show discount info even if the coupon is later deleted or modified.

-- FK (nullable): links to the coupon that was applied on this sale.
-- SET NULL prevents breaking existing sales records if a coupon is ever deleted.
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS coupon_id INTEGER
        REFERENCES coupons (id)
        ON DELETE SET NULL;

-- Historical snapshot: the exact coupon code the customer entered.
-- Stored separately so the info survives even if the coupon row is deleted.
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(100);

-- Historical snapshot: type of discount ('percentage', 'fixed', 'free_shipping').
-- Mirrors coupon_types.discount_type at the time the coupon was applied.
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS coupon_discount_type VARCHAR(50);

-- Historical snapshot: the raw discount_value from the coupon
-- (e.g. 15 for "15%", 500 for "ARS 500 off", 0 for "free_shipping").
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS coupon_discount_value NUMERIC(10, 2);

-- The actual money amount that was saved due to the coupon on this sale.
-- For 'percentage': subtotal * discount_value / 100
-- For 'fixed': discount_value (capped at subtotal)
-- For 'free_shipping': shipping_cost that was waived
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS coupon_discount_amount NUMERIC(10, 2) DEFAULT 0;

-- The total BEFORE applying the coupon discount (i.e. subtotal + shipping_cost).
-- Useful for displaying "you saved X" and for audit/report purposes.
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS original_total NUMERIC(10, 2);

-- Index to speed up coupon usage reports (e.g. "which sales used coupon SUMMER10?")
CREATE INDEX IF NOT EXISTS idx_sales_coupon_id   ON sales (coupon_id);
CREATE INDEX IF NOT EXISTS idx_sales_coupon_code ON sales (coupon_code);
