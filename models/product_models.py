"""
Pydantic models for product-related API operations.
These models define the structure for request/response data.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    """Base product model with common fields."""
    product_name: str = Field(..., description="Name of the product")
    description: Optional[str] = Field(None, description="Product description")
    cost: Optional[float] = Field(None, description="Cost price of the product")
    sale_price: Optional[float] = Field(None, description="Sale price of the product")
    provider_code: Optional[str] = Field(None, description="Provider's product code")
    group_id: Optional[int] = Field(None, description="Product group/category ID")
    provider_id: Optional[int] = Field(None, description="Provider entity ID")
    brand_id: Optional[int] = Field(None, description="Brand ID")
    tax: Optional[float] = Field(None, description="Tax percentage")
    discount: Optional[float] = Field(None, description="Discount amount")
    original_price: Optional[float] = Field(0, description="Original price before discount")
    discount_percentage: Optional[float] = Field(0, description="Discount percentage")
    discount_amount: Optional[float] = Field(0, description="Discount amount")
    has_discount: Optional[int] = Field(0, description="Whether product has discount (0 or 1)")
    comments: Optional[str] = Field(None, description="Additional comments")
    state: Optional[str] = Field("activo", description="Product state")


class ProductCreate(ProductBase):
    """Model for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Model for updating an existing product. All fields are optional."""
    product_name: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    sale_price: Optional[float] = None
    provider_code: Optional[str] = None
    group_id: Optional[int] = None
    provider_id: Optional[int] = None
    brand_id: Optional[int] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    has_discount: Optional[int] = None
    comments: Optional[str] = None
    state: Optional[str] = None


class ProductResponse(ProductBase):
    """Model for product responses from the API."""
    id: int = Field(..., description="Product ID")
    user_id: Optional[int] = Field(None, description="User who created/modified the product")
    images_ids: Optional[int] = Field(None, description="Associated image IDs")
    creation_date: Optional[datetime] = Field(None, description="Product creation date")
    last_modified_date: Optional[datetime] = Field(None, description="Last modification date")
    
    class Config:
        from_attributes = True  # Allows creation from ORM objects


class ProductListResponse(BaseModel):
    """Model for listing multiple products."""
    products: list[ProductResponse]
    total: int = Field(..., description="Total number of products")


# Simplified model for the virtual store (matching your original mock data)
class ProductSimple(BaseModel):
    """Simplified product model for the virtual store frontend."""
    id: int
    name: str
    price: float
    description: str
    image: str
    category: str
    
    class Config:
        from_attributes = True
