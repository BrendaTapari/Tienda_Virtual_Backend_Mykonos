from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProductInfo(BaseModel):
    product_name: str
    sale_price: Any  # Puede ser int, float o str formateado
    size_name: Optional[str] = ""
    color_name: Optional[str] = ""

class ZPLRequest(BaseModel):
    barcode: str
    product_info: Optional[ProductInfo] = None
    options: Optional[Dict[str, Any]] = {}
