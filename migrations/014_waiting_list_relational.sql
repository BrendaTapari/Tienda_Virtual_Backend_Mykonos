-- Migration 014: Add relational tables for waiting list sizes and colors
-- Date: 2026-02-10
-- Description: Create junction tables to support multiple sizes and colors with relational integrity
-- Corrected for PostgreSQL

BEGIN;

-- Create lista_espera_talles table
CREATE TABLE IF NOT EXISTS lista_espera_talles (
    id SERIAL PRIMARY KEY,
    waiting_list_id INTEGER NOT NULL REFERENCES lista_espera(id) ON DELETE CASCADE,
    size_id INTEGER NOT NULL REFERENCES sizes(id) ON DELETE CASCADE,
    UNIQUE(waiting_list_id, size_id)
);

-- Create lista_espera_colores table
CREATE TABLE IF NOT EXISTS lista_espera_colores (
    id SERIAL PRIMARY KEY,
    waiting_list_id INTEGER NOT NULL REFERENCES lista_espera(id) ON DELETE CASCADE,
    color_id INTEGER NOT NULL REFERENCES colors(id) ON DELETE CASCADE,
    UNIQUE(waiting_list_id, color_id)
);

COMMIT;
