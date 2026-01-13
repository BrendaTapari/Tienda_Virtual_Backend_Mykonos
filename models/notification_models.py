from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    user_id: int
    order_id: Optional[int] = None
    type: Optional[str] = None
    title: str
    message: str
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    is_read: bool = False
    email_sent: bool = False

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BroadcastNotificationBase(BaseModel):
    title: str
    message: str
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    target_role: Optional[str] = None
    active: bool = True

class BroadcastNotificationCreate(BroadcastNotificationBase):
    pass

class BroadcastNotificationResponse(BroadcastNotificationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationMarkRead(BaseModel):
    is_read: bool = True

class NotificationImageUpload(BaseModel):
    image_data: str  # Base64 encoded image
    filename: str    # Original filename
