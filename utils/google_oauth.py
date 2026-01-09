"""
Google OAuth 2.0 utility functions for authentication.
Uses the official google-auth library for secure token verification.
"""

import os
from typing import Dict, Optional
from urllib.parse import urlencode
from google.oauth2 import id_token
from google.auth.transport import requests
import httpx


# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_oauth_url(redirect_uri: str, state: Optional[str] = None) -> str:
    """
    Generate Google OAuth authorization URL.
    
    Args:
        redirect_uri: The callback URL where Google will redirect after authentication
        state: Optional state parameter for CSRF protection
    
    Returns:
        Complete Google OAuth URL for user to visit
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID not configured in environment variables")
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    if state:
        params["state"] = state
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict:
    """
    Exchange authorization code for access token and ID token.
    
    Args:
        code: Authorization code from Google
        redirect_uri: The same redirect URI used in the initial request
    
    Returns:
        Dictionary containing access_token, id_token, token_type, expires_in, etc.
    
    Raises:
        httpx.HTTPError: If the token exchange fails
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured")
    
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def verify_google_token(token: str) -> Dict:
    """
    Verify Google ID token and extract user information.
    
    This is the recommended way to verify tokens from Google.
    Uses the official google-auth library for secure verification.
    
    Args:
        token: Google ID token to verify
    
    Returns:
        Dictionary containing verified user info (sub, email, name, picture, etc.)
    
    Raises:
        ValueError: If token verification fails
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID not configured")
    
    try:
        # Verify the token using google-auth library
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            client_id
        )
        
        # Token is valid, return user info
        # 'sub' is Google's unique user ID
        return {
            "id": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False)
        }
    except ValueError as e:
        # Invalid token
        raise ValueError(f"Invalid Google token: {str(e)}")


async def get_google_user_info(access_token: str) -> Dict:
    """
    Fetch user information from Google using access token.
    
    Args:
        access_token: Google OAuth access token
    
    Returns:
        Dictionary containing user info (id, email, name, picture, etc.)
    
    Raises:
        httpx.HTTPError: If fetching user info fails
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()

