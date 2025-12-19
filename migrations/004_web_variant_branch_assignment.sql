BEGIN;

-- Tabla para asignación de stock por sucursal para variantes web
CREATE TABLE IF NOT EXISTS web_variant_branch_assignment (
    id SERIAL PRIMARY KEY,
    variant_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    cantidad_asignada INTEGER NOT NULL DEFAULT 0 CHECK (cantidad_asignada >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_assignment_web_variant FOREIGN KEY (variant_id) REFERENCES web_variants(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_branch FOREIGN KEY (branch_id) REFERENCES storage(id) ON DELETE CASCADE,
    CONSTRAINT uq_variant_branch UNIQUE(variant_id, branch_id)
);

COMMIT;
