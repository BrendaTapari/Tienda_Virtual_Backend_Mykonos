"""
Authentication utilities for FastAPI.
Provides dependency injection functions for protecting endpoints.
"""

from fastapi import Header, HTTPException, status
from typing import Optional
from config.db_connection import DatabaseManager, db
import logging

logger = logging.getLogger(__name__)


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Get current authenticated user from Authorization header.
    
    Args:
        authorization: Bearer token from Authorization header
        
    Returns:
        User dictionary with user information
        
    Raises:
        HTTPException: If token is missing, invalid, or user not found
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, username, fullname, email, phone, domicilio, cuit, 
                   role, status, profile_image_url, email_verified, created_at
            FROM web_users
            WHERE session_token = $1 AND status = 'active'
            """,
            token
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return dict(user)


async def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    """
    Require admin role for endpoint access.
    Use this as a FastAPI dependency to protect admin-only endpoints.
    
    Args:
        authorization: Bearer token from Authorization header
        
    Returns:
        User dictionary with admin user information
        
    Raises:
        HTTPException: If user is not authenticated or not an admin
        
    Example:
        @router.get("/admin-only", dependencies=[Depends(require_admin)])
        async def admin_endpoint():
            return {"message": "Admin access granted"}
    """
    user = await get_current_user(authorization)
    
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


async def get_current_web_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Get current authenticated web user from session token.
    
    Args:
        authorization: Bearer token from Authorization header
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user = await db.fetch_one(
            """
            SELECT id, username, email, fullname, role, status
            FROM web_users
            WHERE session_token = $1 AND status = 'active'
            """,
            token
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )
        
        return dict(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current web user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar autenticación"
        )
