"""
Pydantic models for order/sales management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OrderCustomer(BaseModel):
    """Customer information in order response."""
    id: int
    username: str
    email: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Model for order list response (admin)."""
    order_id: int
    customer: Optional[OrderCustomer] = None
    order_date: datetime
    status: str
    shipping_status: Optional[str] = None
    total: float
    items_count: int = 0
    shipping_address: Optional[str] = None
    origin: str = "local"
    
    class Config:
        from_attributes = True


class OrderItem(BaseModel):
    """Order line item."""
    product_id: int
    product_name: str
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    
    class Config:
        from_attributes = True


class TrackingHistoryItem(BaseModel):
    """Tracking history entry."""
    id: int
    status: str
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    changed_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    """Complete order details (admin)."""
    order_id: int
    customer: Optional[OrderCustomer] = None
    order_date: datetime
    status: str
    shipping_status: Optional[str] = None
    origin: str
    delivery_type: str
    items: List[OrderItem] = []
    subtotal: float
    shipping_cost: float = 0
    discount: float = 0
    total: float
    shipping_address: Optional[str] = None
    external_payment_id: Optional[str] = None
    tracking_history: List[TrackingHistoryItem] = []
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class UpdateOrderStatus(BaseModel):
    """Model for updating order status."""
    status: str = Field(..., description="New shipping status")
    tracking_number: Optional[str] = Field(None, description="Tracking number (optional)")
    notes: Optional[str] = Field(None, description="Additional notes (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "shipped",
                "tracking_number": "AR123456789",
                "notes": "Enviado por Correo Argentino"
            }
        }
