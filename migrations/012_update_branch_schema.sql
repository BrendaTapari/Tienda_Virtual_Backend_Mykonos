-- Rename columns to match Spanish requirements
ALTER TABLE storage RENAME COLUMN name TO sucursal;
ALTER TABLE storage RENAME COLUMN address TO direccion;
ALTER TABLE storage RENAME COLUMN phone_number TO telefono;

-- Add new columns if they don't exist
ALTER TABLE storage ADD COLUMN maps_link TEXT;
ALTER TABLE storage ADD COLUMN horarios TEXT;
ALTER TABLE storage ADD COLUMN instagram TEXT;
