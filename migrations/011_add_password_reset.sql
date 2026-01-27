ALTER TABLE web_users
ADD COLUMN reset_password_token TEXT,
ADD COLUMN reset_password_expires_at TIMESTAMP;
