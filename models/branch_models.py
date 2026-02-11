from pydantic import BaseModel
from typing import Optional, List

from datetime import datetime

class BranchResponse(BaseModel):
    id: int
    sucursal: str
    direccion: Optional[str] = None
    postal_code: Optional[str] = None
    telefono: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    maps_link: Optional[str] = None
    horarios: Optional[str] = None
    instagram: Optional[str] = None

    class Config:
        from_attributes = True

class BranchCreate(BaseModel):
    sucursal: str
    direccion: Optional[str] = None
    maps_link: Optional[str] = None
    horarios: Optional[str] = None
    telefono: Optional[str] = None
    instagram: Optional[str] = None
    postal_code: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None

class BranchUpdate(BaseModel):
    sucursal: Optional[str] = None
    direccion: Optional[str] = None
    maps_link: Optional[str] = None
    horarios: Optional[str] = None
    telefono: Optional[str] = None
    instagram: Optional[str] = None
    postal_code: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class VariantStock(BaseModel):
    variant_id: int
    size: Optional[str]
    color: Optional[str]
    color_hex: Optional[str]
    quantity: int
    barcode: Optional[str]
    cantidad_web: Optional[int]
    mostrar_en_web: Optional[bool]

class BranchWithStock(BaseModel):
    branch_id: int
    branch_name: str
    group_name: Optional[str] = None
    provider_name: Optional[str] = None
    discount_percentage: Optional[float] = 0
    discount_start_date: Optional[datetime] = None
    discount_end_date: Optional[datetime] = None
    variants: List[VariantStock]
