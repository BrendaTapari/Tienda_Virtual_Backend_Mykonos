"""
User authentication routes for web users.
Handles registration, login, logout, and user profile management.
Uses FastAPI-Mail for email verification and notifications.
"""

from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional
import bcrypt
import uuid
from datetime import datetime

from models.user_models import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserUpdate,
    PasswordChange,
    EmailVerification,
    ResendVerification
)
from config.db_connection import DatabaseManager
from utils.email import send_verification_email

router = APIRouter()


# Helper functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def generate_session_token() -> str:
    """Generate a unique session token."""
    return str(uuid.uuid4())


def generate_verification_token() -> str:
    """Generate a unique email verification token."""
    return str(uuid.uuid4())


async def get_user_by_token(token: str):
    """Get user by session token."""
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


# Endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new web user.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 6 characters)
    - **fullname**: Full name (optional)
    - **phone**: Phone number (optional)
    - **domicilio**: Address (optional)
    - **cuit**: CUIT (optional)
    
    After registration, user will receive a verification email.
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Check if username already exists
        existing_user = await conn.fetchrow(
            "SELECT id FROM web_users WHERE username = $1",
            user_data.username
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await conn.fetchrow(
            "SELECT id FROM web_users WHERE email = $1",
            user_data.email
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and generate tokens
        hashed_password = hash_password(user_data.password)
        session_token = generate_session_token()
        verification_token = generate_verification_token()
        
        # Insert new user
        new_user = await conn.fetchrow(
            """
            INSERT INTO web_users 
            (username, fullname, email, password, phone, domicilio, cuit, 
             role, status, session_token, email_verified, verification_token)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, username, fullname, email, phone, domicilio, cuit, 
                      role, status, profile_image_url, email_verified, created_at
            """,
            user_data.username,
            user_data.fullname,
            user_data.email,
            hashed_password,
            user_data.phone,
            user_data.domicilio,
            user_data.cuit,
            "customer",  # Default role
            "active",    # Default status
            session_token,
            False,       # email_verified
            verification_token
        )
        
        user_response = UserResponse(**dict(new_user))
        
        # Send verification email
        try:
            await send_verification_email(
                email=user_data.email,
                username=user_data.username,
                verification_token=verification_token
            )
        except Exception as e:
            # Log error but don't fail registration
            print(f"Error sending verification email: {e}")
        
        return TokenResponse(
            token=session_token,
            user=user_response,
            message="Registration successful. Please check your email to verify your account."
        )


@router.post("/verify-email")
async def verify_email(verification_data: EmailVerification):
    """
    Verify user email with verification token.
    
    - **token**: Verification token from email
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Find user by verification token
        user = await conn.fetchrow(
            "SELECT id, username, email, email_verified FROM web_users WHERE verification_token = $1",
            verification_data.token
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        if user['email_verified']:
            return {"message": "Email already verified"}
        
        # Update user as verified
        await conn.execute(
            """
            UPDATE web_users 
            SET email_verified = TRUE, verification_token = NULL 
            WHERE id = $1
            """,
            user['id']
        )
    
    # Send welcome email after successful verification
    try:
        from utils.email import send_welcome_email
        await send_welcome_email(
            email=user['email'],
            username=user['username']
        )
    except Exception as e:
        # Log error but don't fail verification
        print(f"Error sending welcome email: {e}")
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(resend_data: ResendVerification):
    """
    Resend verification email.
    
    - **email**: Email address to resend verification
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Find user by email
        user = await conn.fetchrow(
            "SELECT id, username, email, email_verified, verification_token FROM web_users WHERE email = $1",
            resend_data.email
        )
        
        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a verification link has been sent"}
        
        if user['email_verified']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Generate new verification token if needed
        verification_token = user['verification_token'] or generate_verification_token()
        
        await conn.execute(
            "UPDATE web_users SET verification_token = $1 WHERE id = $2",
            verification_token,
            user['id']
        )
        
        # Send verification email
        try:
            await send_verification_email(
                email=user['email'],
                username=user['username'],
                verification_token=verification_token
            )
        except Exception as e:
            # Log error but don't reveal to user
            print(f"Error sending verification email: {e}")
    
    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login with username/email and password.
    
    - **username**: Username or email
    - **password**: User password
    
    Note: Email must be verified to login (can be disabled for development).
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Try to find user by username or email
        user = await conn.fetchrow(
            """
            SELECT id, username, fullname, email, phone, domicilio, cuit, 
                   role, status, profile_image_url, email_verified, created_at, password
            FROM web_users
            WHERE (username = $1 OR email = $1)
            """,
            credentials.username
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user is active
        if user['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        
        # TODO: Uncomment this when email verification is fully implemented
        # Check if email is verified
        # if not user['email_verified']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Please verify your email before logging in"
        #     )
        
        # Generate new session token
        session_token = generate_session_token()
        
        # Update session token in database
        await conn.execute(
            "UPDATE web_users SET session_token = $1 WHERE id = $2",
            session_token,
            user['id']
        )
        
        # Remove password from user data
        user_dict = dict(user)
        user_dict.pop('password')
        user_response = UserResponse(**user_dict)
        
        return TokenResponse(
            token=session_token,
            user=user_response,
            message="Login successful"
        )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout and invalidate session token.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Clear session token
        result = await conn.execute(
            "UPDATE web_users SET session_token = NULL WHERE session_token = $1",
            token
        )
        
        if result == "UPDATE 0":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current authenticated user information.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    user = await get_user_by_token(token)
    
    return UserResponse(**user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    authorization: Optional[str] = Header(None)
):
    """
    Update current user information.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    # Build update query dynamically based on provided fields
    update_fields = []
    values = []
    param_count = 1
    
    if user_update.fullname is not None:
        update_fields.append(f"fullname = ${param_count}")
        values.append(user_update.fullname)
        param_count += 1
    
    if user_update.email is not None:
        # Check if email is already used by another user
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM web_users WHERE email = $1 AND id != $2",
                user_update.email,
                current_user['id']
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        update_fields.append(f"email = ${param_count}")
        values.append(user_update.email)
        param_count += 1
    
    if user_update.phone is not None:
        update_fields.append(f"phone = ${param_count}")
        values.append(user_update.phone)
        param_count += 1
    
    if user_update.domicilio is not None:
        update_fields.append(f"domicilio = ${param_count}")
        values.append(user_update.domicilio)
        param_count += 1
    
    if user_update.profile_image_url is not None:
        update_fields.append(f"profile_image_url = ${param_count}")
        values.append(user_update.profile_image_url)
        param_count += 1
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add user ID as last parameter
    values.append(current_user['id'])
    
    query = f"""
        UPDATE web_users 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, username, fullname, email, phone, domicilio, cuit, 
                  role, status, profile_image_url, email_verified, created_at
    """
    
    async with pool.acquire() as conn:
        updated_user = await conn.fetchrow(query, *values)
    
    return UserResponse(**dict(updated_user))


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    authorization: Optional[str] = Header(None)
):
    """
    Change user password.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get current password hash
        user = await conn.fetchrow(
            "SELECT password FROM web_users WHERE id = $1",
            current_user['id']
        )
        
        # Verify current password
        if not verify_password(password_data.current_password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hashed_password = hash_password(password_data.new_password)
        
        # Update password
        await conn.execute(
            "UPDATE web_users SET password = $1 WHERE id = $2",
            new_hashed_password,
            current_user['id']
        )
    
    return {"message": "Password changed successfully"}


# TODO: Google OAuth endpoint - Implement when Google OAuth is configured
# @router.post("/auth/google")
# async def google_auth(google_token: str):
#     """
#     Authenticate with Google OAuth.
#     
#     This endpoint will:
#     1. Verify the Google token
#     2. Extract user information (email, name, google_id)
#     3. Create user if doesn't exist or login if exists
#     4. Return session token
#     
#     See GOOGLE_OAUTH_SETUP.md for configuration instructions.
#     """
#     pass


@router.get("/{user_id}/activity")
async def get_user_activity(user_id: int):
    """
    Get complete user activity information (admin only).
    
    Returns comprehensive user data including:
    - User profile information
    - Purchase history with full tracking history
    - Payment methods used
    - All products ordered with details
    
    Path Parameters:
    - user_id: The ID of the user to retrieve activity for
    
    Requires: Admin authentication (TODO: add authentication)
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get user profile
        user = await conn.fetchrow(
            """
            SELECT id, username, fullname, email, phone, domicilio, cuit, 
                   role, status, profile_image_url, email_verified, created_at
            FROM web_users
            WHERE id = $1
            """,
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Get purchase history
        purchases = await conn.fetch(
            """
            SELECT 
                s.id as sale_id,
                s.sale_date as purchase_date,
                s.total,
                s.origin,
                s.shipping_address,
                s.delivery_type,
                s.notes
            FROM sales s
            WHERE s.web_user_id = $1
            ORDER BY s.sale_date DESC
            """,
            user_id
        )
        
        # Get all products ordered
        products_ordered = await conn.fetch(
            """
            SELECT 
                sd.sale_id,
                sd.product_id,
                sd.product_name,
                sd.variant_id,
                sd.size_name as size,
                sd.color_name as color,
                sd.quantity,
                sd.sale_price as unit_price,
                sd.subtotal,
                sd.discount_amount as discount_applied,
                s.sale_date as order_date
            FROM sales_detail sd
            JOIN sales s ON s.id = sd.sale_id
            WHERE s.web_user_id = $1
            ORDER BY s.sale_date DESC, sd.id
            """,
            user_id
        )
        
        # Format response
        user_data = dict(user)
        
        # Format purchases with tracking history and payment info
        purchases_list = []
        for purchase in purchases:
            sale_id = purchase['sale_id']
            
            # Get full tracking history for this purchase
            tracking_history = await conn.fetch(
                """
                SELECT 
                    status,
                    description,
                    location,
                    created_at
                FROM sales_tracking_history
                WHERE sale_id = $1
                ORDER BY created_at ASC
                """,
                sale_id
            )
            
            # Get payment information
            payment_info = await conn.fetch(
                """
                SELECT 
                    sp.id as payment_id,
                    pm.method_name,
                    pm.display_name,
                    b.name as bank_name,
                    sp.created_at as payment_date
                FROM sales_payments sp
                JOIN banks_payment_methods bpm ON bpm.id = sp.payment_method_id
                JOIN payment_methods pm ON pm.id = bpm.payment_method_id
                LEFT JOIN banks b ON b.id = bpm.bank_id
                WHERE sp.sale_id = $1
                """,
                sale_id
            )
            
            # Format tracking history
            tracking_list = []
            for track in tracking_history:
                tracking_list.append({
                    "status": track['status'],
                    "description": track['description'],
                    "location": track['location'],
                    "timestamp": track['created_at'].isoformat() if track['created_at'] else None
                })
            
            # Format payment info
            payment_list = []
            for payment in payment_info:
                payment_list.append({
                    "payment_id": payment['payment_id'],
                    "method_name": payment['method_name'],
                    "display_name": payment['display_name'],
                    "bank_name": payment['bank_name'],
                    "payment_date": payment['payment_date'].isoformat() if payment['payment_date'] else None
                })
            
            # Get current status (last tracking entry)
            current_status = tracking_list[-1] if tracking_list else None
            
            purchases_list.append({
                "sale_id": sale_id,
                "purchase_date": purchase['purchase_date'].isoformat() if purchase['purchase_date'] else None,
                "total": float(purchase['total']) if purchase['total'] else 0,
                "origin": purchase['origin'],
                "shipping_address": purchase['shipping_address'],
                "delivery_type": purchase['delivery_type'],
                "notes": purchase['notes'],
                "current_status": current_status['status'] if current_status else None,
                "current_status_description": current_status['description'] if current_status else None,
                "current_status_updated_at": current_status['timestamp'] if current_status else None,
                "tracking_history": tracking_list,
                "payment_methods": payment_list
            })
        
        # Format products
        products_list = []
        for product in products_ordered:
            products_list.append({
                "sale_id": product['sale_id'],
                "product_id": product['product_id'],
                "product_name": product['product_name'],
                "variant_id": product['variant_id'],
                "size": product['size'],
                "color": product['color'],
                "quantity": product['quantity'],
                "unit_price": float(product['unit_price']) if product['unit_price'] else 0,
                "subtotal": float(product['subtotal']) if product['subtotal'] else 0,
                "discount_applied": float(product['discount_applied']) if product['discount_applied'] else 0,
                "order_date": product['order_date'].isoformat() if product['order_date'] else None
            })
        
        # Calculate statistics
        total_purchases = len(purchases_list)
        total_spent = sum(p['total'] for p in purchases_list)
        total_products = sum(p['quantity'] for p in products_list)
        
        return {
            "user": {
                "id": user_data['id'],
                "username": user_data['username'],
                "fullname": user_data['fullname'],
                "email": user_data['email'],
                "phone": user_data['phone'],
                "domicilio": user_data['domicilio'],
                "cuit": user_data['cuit'],
                "role": user_data['role'],
                "status": user_data['status'],
                "email_verified": user_data['email_verified'],
                "created_at": user_data['created_at'].isoformat() if user_data['created_at'] else None
            },
            "statistics": {
                "total_purchases": total_purchases,
                "total_spent": total_spent,
                "total_products_ordered": total_products
            },
            "purchases": purchases_list,
            "products_ordered": products_list
        }
