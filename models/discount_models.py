"""
Pydantic models for discount management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateGroupDiscount(BaseModel):
    """Model for creating a group discount."""
    group_id: int = Field(..., description="Group ID to apply discount to")
    discount_percentage: float = Field(..., gt=0, lt=100, description="Discount percentage (0-100)")
    start_date: Optional[datetime] = Field(None, description="Start date (optional)")
    end_date: Optional[datetime] = Field(None, description="End date (optional)")
    apply_to_children: bool = Field(False, description="Apply to subgroups as well")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_id": 5,
                "discount_percentage": 10,
                "start_date": "2024-12-15T00:00:00",
                "end_date": "2024-12-31T23:59:59",
                "apply_to_children": True
            }
        }


class DiscountResponse(BaseModel):
    """Model for discount list response."""
    discount_id: int
    type: str  # 'group', 'product', 'category'
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    discount_percentage: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool
    affected_products: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class UpdateDiscount(BaseModel):
    """Model for updating a discount."""
    discount_percentage: Optional[float] = Field(None, gt=0, lt=100, description="New discount percentage")
    end_date: Optional[datetime] = Field(None, description="New end date")
    is_active: Optional[bool] = Field(None, description="Activate or pause discount")
    
    class Config:
        json_schema_extra = {
            "example": {
                "discount_percentage": 15,
                "end_date": "2025-01-15T23:59:59",
                "is_active": False
            }
        }
