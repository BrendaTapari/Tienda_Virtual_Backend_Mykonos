"""
Web Tags API routes.
Handles CRUD for web_tags and product_tags tables.
Registered at prefix /web-tags in main.py to avoid
collision with /products/{product_id}.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from config.db_connection import db
from utils.auth import require_admin
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Models ────────────────────────────────────────────────────

class TagCreate(BaseModel):
    tag_name: str = Field(..., description="Nombre del tag (ej: noche, elegante)")


# ─── Endpoints ─────────────────────────────────────────────────

@router.get("/")
async def list_tags():
    """
    Lista todos los tags disponibles con la cantidad de productos por tag.
    """
    try:
        rows = await db.fetch_all(
            """
            SELECT wt.id, wt.tag_name,
                   COUNT(pt.product_id) AS product_count
            FROM web_tags wt
            LEFT JOIN product_tags pt ON pt.tag_id = wt.id
            GROUP BY wt.id, wt.tag_name
            ORDER BY wt.tag_name ASC
            """
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error listing tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", dependencies=[Depends(require_admin)], status_code=201)
async def create_tag(tag: TagCreate):
    """
    Crea un nuevo tag web. El nombre debe ser único (se guarda en minúsculas).
    """
    try:
        result = await db.fetch_one(
            """
            INSERT INTO web_tags (tag_name)
            VALUES ($1)
            RETURNING id, tag_name, created_at
            """,
            tag.tag_name.strip().lower()
        )
        return dict(result)
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"El tag '{tag.tag_name}' ya existe")
        logger.error(f"Error creating tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tag_id}", dependencies=[Depends(require_admin)])
async def delete_tag(tag_id: int):
    """
    Elimina un tag y desasocia todos los productos que lo tenían.
    """
    try:
        existing = await db.fetch_one("SELECT id FROM web_tags WHERE id = $1", tag_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Tag no encontrado")

        await db.execute("DELETE FROM product_tags WHERE tag_id = $1", tag_id)
        await db.execute("DELETE FROM web_tags WHERE id = $1", tag_id)
        return {"message": f"Tag {tag_id} eliminado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tag {tag_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
