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


class CreateOrderRequest(BaseModel):
    """Model for creating a purchase order from cart."""
    shipping_address: Optional[str] = Field(None, description="Dirección de envío completa (Legacy)")
    delivery_type: str = Field(..., description="Tipo de entrega: 'envio' o 'retiro'")
    shipping_cost: float = Field(0, ge=0, description="Costo de envío")
    notes: Optional[str] = Field(None, description="Notas adicionales para el pedido")
    payment_method: Optional[str] = Field(None, description="Método de pago (para futuro uso)")
    branch_id: Optional[int] = Field(None, description="ID de la sucursal para retiro (opcional)")
    
    # New address fields
    provincia: Optional[str] = Field(None, description="Province")
    ciudad: Optional[str] = Field(None, description="City")
    calle: Optional[str] = Field(None, description="Street")
    numero: Optional[str] = Field(None, description="Number")
    piso: Optional[str] = Field(None, description="Floor")
    departamento: Optional[str] = Field(None, description="Apartment")
    codigo_postal: Optional[str] = Field(None, description="Zip Code")
    phone: Optional[str] = Field(None, description="Customer phone number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shipping_address": "Av. Corrientes 1234, Piso 5 Depto B, CABA, Buenos Aires",
                "delivery_type": "envio",
                "shipping_cost": 500.00,
                "notes": "Dejar en portería si no hay nadie. Horario preferido: 14-18hs"
            }
        }


class TrackingUpdateRequest(BaseModel):
    """Model for updating order tracking history."""
    status: str = Field(..., description="Estado del envío: 'preparando', 'despachado', 'en_transito', 'entregado', 'cancelado'")
    description: str = Field(..., description="Descripción del estado")
    location: Optional[str] = Field(None, description="Ubicación actual del pedido")
    notify_customer: bool = Field(True, description="Si enviar email de notificación al cliente")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "despachado",
                "description": "Tu pedido ha sido despachado y está en camino. Número de seguimiento: AR123456789",
                "location": "Centro de Distribución - CABA",
                "notify_customer": True
            }
        }


class OrderItemResponse(BaseModel):
    """Model for order item in response."""
    product_id: int
    product_name: str
    product_code: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    variant_barcode: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    
    class Config:
        from_attributes = True


class CreateOrderResponse(BaseModel):
    """Model for create order response."""
    message: str
    order_id: int
    order_details: dict
    tracking_link: str
    
    class Config:
        from_attributes = True


class PaymentConfirmationRequest(BaseModel):
    """Model for confirming payment on an order."""
    payment_proof_url: Optional[str] = Field(None, description="URL del comprobante de pago")
    payment_method: str = Field(..., description="Método de pago utilizado")
    payment_reference: Optional[str] = Field(None, description="Referencia de pago (ej: MP-123456)")
    notes: Optional[str] = Field(None, description="Notas adicionales sobre el pago")
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_method": "mercadopago",
                "payment_reference": "MP-123456789",
                "payment_proof_url": "https://storage.com/comprobante-123.pdf",
                "notes": "Pago realizado exitosamente"
            }
        }


class CancelOrderRequest(BaseModel):
    """Model for cancelling an order."""
    reason: str = Field(..., description="Razón de cancelación: 'expired', 'user_cancelled', 'payment_failed'")
    notes: Optional[str] = Field(None, description="Notas adicionales")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "user_cancelled",
                "notes": "Cliente solicitó cancelación"
            }
        }

