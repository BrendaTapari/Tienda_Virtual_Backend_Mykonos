-- Migration 020: Add description to coupons

ALTER TABLE coupons
ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
