from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- SCHEMAS (Pydantic) ---

class StockSucursalInput(BaseModel):
    sucursal_id: int
    cantidad_asignada: int

class VarianteUpdateInput(BaseModel):
    id: int
    mostrar_en_web: bool
    configuracion_stock: List[StockSucursalInput]

class ProductoUpdateSchema(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio_web: float
    en_tienda_online: bool
    variantes: List[VarianteUpdateInput]

    # Configuración V2
    model_config = ConfigDict(from_attributes=True)