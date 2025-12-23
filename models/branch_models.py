from pydantic import BaseModel
from typing import Optional, List

from datetime import datetime

class BranchResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    postal_code: Optional[str] = None
    phone_number: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

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
