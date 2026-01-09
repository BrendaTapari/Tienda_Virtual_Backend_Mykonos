from pydantic import BaseModel
from typing import Optional


class ImageUpload(BaseModel):
    """Modelo para subir imagen en base64"""
    image_data: str  # Base64 encoded image
    filename: str    # Original filename
    orden: Optional[int] = None  # Orden de visualización (opcional, se auto-asigna si no se especifica)