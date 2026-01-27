-- Add split address fields to web_users table
ALTER TABLE web_users
ADD COLUMN provincia TEXT,
ADD COLUMN ciudad TEXT,
ADD COLUMN calle TEXT,
ADD COLUMN numero TEXT,
ADD COLUMN piso TEXT,
ADD COLUMN departamento TEXT,
ADD COLUMN codigo_postal TEXT;
