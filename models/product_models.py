"""
Pydantic models for product-related API operations.
These models define the structure for request/response data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
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
    # Online store fields
    en_tienda_online: Optional[bool] = Field(False, description="Whether product is available in online store")
    nombre_web: Optional[str] = Field(None, description="Product name for online store")
    descripcion_web: Optional[str] = Field(None, description="Product description for online store")
    slug: Optional[str] = Field(None, description="URL-friendly slug for the product")
    precio_web: Optional[float] = Field(None, description="Price for online store")


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
    # Online store fields
    en_tienda_online: Optional[bool] = None
    nombre_web: Optional[str] = None
    descripcion_web: Optional[str] = None
    slug: Optional[str] = None
    precio_web: Optional[float] = None


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


# Image models
class ProductImage(BaseModel):
    """Model for product images."""
    id: int = Field(..., description="Image ID")
    image_url: str = Field(..., description="URL of the image")
    product_id: int = Field(..., description="Product ID this image belongs to")
    
    class Config:
        from_attributes = True


class AddProductImage(BaseModel):
    """Model for adding an image to a product."""
    image_url: str = Field(..., description="URL of the image to add")


# Product with images
class ProductWithImages(BaseModel):
    """Product model with image URLs."""
    id: int
    product_name: str
    nombre_web: Optional[str] = None
    description: Optional[str] = None
    descripcion_web: Optional[str] = None
    sale_price: Optional[float] = None
    precio_web: Optional[float] = None
    slug: Optional[str] = None
    en_tienda_online: bool = False
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    category: Optional[str] = None
    state: Optional[str] = None
    
    class Config:
        from_attributes = True


# Online store product model
class OnlineStoreProductVariant(BaseModel):
    variant_id: int        # ID de la variante (puede ser de web_variants o warehouse_stock_variants)
    talle: str
    color: str
    color_hex: str
    stock: int             # Stock calculado
    barcode: Optional[str] = None

    class Config:
        orm_mode = True

class OnlineStoreProduct(BaseModel):
    id: int
    nombre_web: str
    descripcion_web: Optional[str] = None
    precio_web: Optional[float] = None
    slug: Optional[str] = None
    category: str
    images: List[str] = []
    stock_disponible: int  # Suma total del stock
    variantes: List[OnlineStoreProductVariant] # Lista de variantes
    discount_percentage: Optional[float] = 0

    class Config:
        orm_mode = True


# Detailed product model with all information
class ProductDetail(BaseModel):
    """Complete product information including variants, colors, sizes, and stock."""
    id: int
    nombre_web: str
    descripcion_web: str
    precio_web: Optional[float] = None
    slug: str
    category: Optional[str] = None
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    stock_disponible: int = Field(0, description="Total available stock")
    # Additional detailed fields
    colores: List[dict] = Field(default_factory=list, description="Available colors with hex codes")
    talles: List[str] = Field(default_factory=list, description="Available sizes")
    variantes: List[dict] = Field(default_factory=list, description="Product variants with stock")
    
    class Config:
        from_attributes = True


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


# Admin endpoint models
class ProductAllResponse(BaseModel):
    """Model for GET /products/all endpoint - returns all products for admin."""
    id: int
    product_name: str
    provider_code: Optional[str] = None
    sale_price: Optional[float] = None
    en_tienda_online: bool = False
    group_id: Optional[int] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ToggleOnlineRequest(BaseModel):
    """Model for PATCH /products/{id}/toggle-online endpoint."""
    en_tienda_online: bool = Field(..., description="Whether to activate/deactivate product in online store")
    nombre_web: Optional[str] = Field(None, description="Product name for online store")
    descripcion_web: Optional[str] = Field(None, description="Product description for online store")
    precio_web: Optional[float] = Field(None, description="Price for online store")
    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")


class ProductInfoMatrix(BaseModel):
    """Model for the product info matrix endpoint."""
    id: int
    product_name: str
    precio_web: Optional[float] = None
    discount: Optional[float] = Field(0, description="Discount percentage")
    stock: int = Field(0, description="Web stock available")
    group: Optional[str] = None
    provider: Optional[str] = None

    class Config:
        from_attributes = True
