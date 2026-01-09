"""
Pydantic models for user authentication and management.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """Model for user registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    fullname: Optional[str] = Field(None, min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    domicilio: Optional[str] = Field(None, max_length=200, description="Address")
    cuit: Optional[str] = Field(None, min_length=11, max_length=11, description="CUIT (11 digits)")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "juanperez",
                "fullname": "Juan Pérez",
                "email": "juan@example.com",
                "password": "securepass123"
            }
        }


class UserLogin(BaseModel):
    """Model for user login request."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "juanperez",
                "password": "securepass123"
            }
        }


class UserResponse(BaseModel):
    """Response model for user data (excludes sensitive fields like password)."""
    id: int
    username: str
    fullname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    domicilio: Optional[str] = None
    cuit: Optional[str] = None
    role: str = "customer"
    status: str = "active"
    profile_image_url: Optional[str] = None
    email_verified: bool = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "juanperez",
                "fullname": "Juan Pérez",
                "email": "juan@example.com",
                "email_verified": False,
                "role": "customer",
                "status": "active",
                "created_at": "2024-12-08T10:30:00"
            }
        }


class TokenResponse(BaseModel):
    """Model for authentication response with token."""
    token: str = Field(..., description="Session token")
    user: UserResponse = Field(..., description="User data")
    message: str = Field(default="Authentication successful")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456ghi789",
                "user": {
                    "id": 1,
                    "username": "juanperez",
                    "fullname": "Juan Pérez",
                    "email": "juan@example.com",
                    "cuit": "20123456789"
                },
                "message": "Authentication successful"
            }
        }


class UserUpdate(BaseModel):
    """Model for updating user information."""
    fullname: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    domicilio: Optional[str] = Field(None, max_length=200)
    profile_image_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "fullname": "Juan Carlos Pérez",
                "phone": "3434567891",
                "domicilio": "Avenida Siempreviva 742"
            }
        }


class PasswordChange(BaseModel):
    """Model for password change request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpass123",
                "new_password": "newpass456"
            }
        }


class EmailVerification(BaseModel):
    """Model for email verification request."""
    token: str = Field(..., description="Verification token from email")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456ghi789"
            }
        }


class ResendVerification(BaseModel):
    """Model for resending verification email."""
    email: EmailStr = Field(..., description="Email address to resend verification")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "juan@example.com"
            }
        }


# Admin user management models
class UserListResponse(BaseModel):
    """Model for admin user list response."""
    id: int
    username: str
    fullname: Optional[str] = None
    email: Optional[str] = None
    role: str
    status: str
    email_verified: bool
    created_at: Optional[datetime] = None
    total_purchases: int = 0
    
    class Config:
        from_attributes = True


class UpdateUserRole(BaseModel):
    """Model for updating user role."""
    role: str = Field(..., description="New role (admin or customer)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "admin"
            }
        }


class UpdateUserStatus(BaseModel):
    """Model for updating user status."""
    status: str = Field(..., description="New status (active or inactive)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "inactive"
            }
        }


# Google OAuth models
class GoogleAuthCallback(BaseModel):
    """Model for Google OAuth callback parameters."""
    code: str = Field(..., description="Authorization code from Google")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "4/0AY0e-g7xxxxxxxxxxxxxxxxxxx"
            }
        }


class GoogleUserInfo(BaseModel):
    """Model for Google user information."""
    id: str = Field(..., description="Google user ID")
    email: str = Field(..., description="User email from Google")
    name: Optional[str] = Field(None, description="User's full name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    verified_email: bool = Field(default=True, description="Whether email is verified by Google")
