"""
Pydantic models for shipping configuration.
"""

from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class ShippingConfigUpdate(BaseModel):
    """Model for updating shipping configuration."""
    policy: Literal["threshold", "always_free", "always_paid", "split"] = Field(
        ..., description="Política de envío: threshold, always_free, always_paid, o split"
    )
    free_threshold: float = Field(
        ..., description="Umbral para envío gratis (solo aplica con policy='threshold')"
    )
    provider_name: str = Field(
        ..., description="Nombre del proveedor de envíos (ej. Correo Argentino)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "policy": "threshold",
                "free_threshold": 300000.0,
                "provider_name": "Correo Argentino"
            }
        }


class ShippingConfigResponse(ShippingConfigUpdate):
    """Model for shipping configuration response."""
    updated_at: datetime
    
    class Config:
        from_attributes = True
