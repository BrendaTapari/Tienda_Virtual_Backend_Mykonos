-- Migration 019: Track coupon deactivation time for admin visibility window

ALTER TABLE coupons
ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP;

-- Useful for filtering inactive coupons by recent deactivation window
CREATE INDEX IF NOT EXISTS idx_coupons_deactivated_at ON coupons (deactivated_at);
