from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PromotionBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = 0
    is_active: Optional[bool] = True

class PromotionCreate(PromotionBase):
    pass

class PromotionUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class PromotionResponse(PromotionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
