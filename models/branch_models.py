from pydantic import BaseModel
from typing import Optional, List

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
    variants: List[VariantStock]
