from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Creamos el Router (es como una mini-app)
router = APIRouter()

# --- MODELO (Lo movemos aquí o a un archivo models.py si prefieres) ---
class Product(BaseModel):
    id: Optional[int] = None
    name: str
    price: float
    description: str
    image: str
    category: str

# --- BASE DE DATOS MOCK (Específica de este archivo) ---
fake_db = [
    {
        "id": 1, 
        "name": "Blusa Seda Mykonos", 
        "price": 45000, 
        "description": "Elegancia pura.", 
        "image": "https://images.unsplash.com/photo-1564257631407-4deb1f99d992", 
        "category": "Noche"
    },
    {
        "id": 2, 
        "name": "Pantalón Palazzo", 
        "price": 52000, 
        "description": "Comodidad.", 
        "image": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1", 
        "category": "Casual"
    }
]

# --- RUTAS ---
# NOTA: Aquí ponemos "/" y automáticamente será "/products/"
# gracias a la configuración que haremos en el main.py

@router.get("/", response_model=List[Product])
def get_products():
    return fake_db

@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int):
    product = next((item for item in fake_db if item["id"] == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@router.post("/", response_model=Product)
def create_product(product: Product):
    new_id = len(fake_db) + 1
    new_product_data = product.dict()
    new_product_data["id"] = new_id
    fake_db.append(new_product_data)
    return new_product_data