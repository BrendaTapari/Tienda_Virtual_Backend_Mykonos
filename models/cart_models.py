"""
Pydantic models for shopping cart management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CartItemResponse(BaseModel):
    """Model for cart item in response."""
    cart_item_id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    variant_id: Optional[int] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    stock_available: int
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Model for complete cart response."""
    cart_id: int
    user_id: int
    items: List[CartItemResponse] = []
    total_items: int = 0
    subtotal: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    """Model for adding product to cart."""
    product_id: int = Field(..., description="Product ID")
    variant_id: int = Field(..., description="Variant ID (size/color combination)")
    quantity: int = Field(1, ge=1, description="Quantity to add")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 45,
                "variant_id": 12,
                "quantity": 1
            }
        }


class UpdateCartItemRequest(BaseModel):
    """Model for updating cart item quantity."""
    quantity: int = Field(..., ge=1, description="New quantity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 3
            }
        }


class CheckoutRequest(BaseModel):
    """Model for checkout request."""
    shipping_address: str = Field(..., description="Shipping address")
    payment_method: str = Field(..., description="Payment method (efectivo, transferencia, mercadopago)")
    notes: Optional[str] = Field(None, description="Optional notes for the order")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shipping_address": "Calle Falsa 123, Paraná, Entre Ríos",
                "payment_method": "efectivo",
                "notes": "Entregar por la tarde"
            }
        }
