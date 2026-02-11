-- Migration 013: Add codigo_barra_variante to lista_espera table
-- Date: 2026-02-10
-- Description: Add codigo_barra_variante column to support tracking specific variant barcodes in waiting list

-- Add the codigo_barra_variante column if it doesn't already exist
-- Using PostgreSQL syntax for adding column
DO $$ 
BEGIN
    -- Check if column exists, if not add it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='lista_espera' AND column_name='codigo_barra_variante'
    ) THEN
        ALTER TABLE lista_espera ADD COLUMN codigo_barra_variante VARCHAR(50);
        RAISE NOTICE 'Column codigo_barra_variante added successfully';
    ELSE
        RAISE NOTICE 'Column codigo_barra_variante already exists, skipping';
    END IF;
END $$;
