BEGIN;

-- Add google_id column to web_users table for Google OAuth authentication
-- This stores Google's unique user identifier
ALTER TABLE web_users ADD COLUMN IF NOT EXISTS google_id TEXT UNIQUE;

-- Create index for faster lookups by google_id
CREATE INDEX IF NOT EXISTS idx_web_users_google_id ON web_users(google_id);

-- Note: The existing 'profile_image_url' column (from migration 001) is used
-- to store the user's Google profile picture URL when authenticating via OAuth

COMMIT;
