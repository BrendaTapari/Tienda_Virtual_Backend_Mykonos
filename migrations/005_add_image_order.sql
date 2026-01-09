BEGIN;

-- ---------------------------------------------------------
-- Agregar columna 'orden' a la tabla images
-- ---------------------------------------------------------

-- Agregar la columna orden con valor por defecto 0
ALTER TABLE images ADD COLUMN IF NOT EXISTS orden INTEGER NOT NULL DEFAULT 0;

-- Actualizar las imágenes existentes para asignar un orden basado en su ID actual
-- Esto mantiene el orden actual de las imágenes
UPDATE images 
SET orden = subquery.row_num
FROM (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY id ASC) as row_num
    FROM images
) AS subquery
WHERE images.id = subquery.id;

-- Crear índice para optimizar las consultas de ordenamiento por producto
CREATE INDEX IF NOT EXISTS idx_images_product_orden ON images(product_id, orden);

-- Comentario descriptivo
COMMENT ON COLUMN images.orden IS 'Orden de visualización de la imagen dentro del producto. Menor valor = mayor prioridad.';

COMMIT;
