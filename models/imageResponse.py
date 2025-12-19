from pydantic import BaseModel
from typing import Optional


class ImageResponse(BaseModel):
    """Respuesta con datos de imagen"""
    id: int
    image_url: str
