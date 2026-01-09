from pydantic import BaseModel
from typing import List


class ImageOrderUpdate(BaseModel):
    """Modelo para actualizar el orden de una imagen"""
    image_id: int
    orden: int


class ReorderImagesRequest(BaseModel):
    """Modelo para reordenar múltiples imágenes de un producto"""
    images: List[ImageOrderUpdate]
