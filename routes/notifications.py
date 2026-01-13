from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import List, Optional
from datetime import datetime, timedelta
from config.db_connection import db
from database.database import TABLES
from models.notification_models import (
    NotificationResponse,
    NotificationCreate,
    NotificationMarkRead,
    BroadcastNotificationCreate,
    BroadcastNotificationResponse,
    NotificationImageUpload
)
from utils.auth import get_current_web_user, require_admin
import logging
import base64
import os
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[NotificationResponse])
async def get_my_notifications(authorization: Optional[str] = Header(None)):
    """
    Get all personal notifications for the current user.
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']

        query = f"""
            SELECT * FROM {TABLES.NOTIFICATIONS.value} 
            WHERE user_id = $1 
            ORDER BY created_at DESC
        """
        notifications = await db.fetch_all(query, user_id)
        return notifications
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving notifications"
        )

@router.get("/unread-count")
async def get_unread_count(authorization: Optional[str] = Header(None)):
    """
    Get the count of unread notifications (personal + broadcasts).
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']
        user_role = user.get('role', 'customer')

        # Count personal unread
        personal_query = f"""
            SELECT COUNT(*) as count FROM {TABLES.NOTIFICATIONS.value} 
            WHERE user_id = $1 AND is_read = FALSE
        """
        personal_count = await db.fetch_one(personal_query, user_id)
        
        # Count unread broadcasts
        # Broadcasts that target the user's role (or 'all') AND are NOT in user_broadcasts with is_read=TRUE
        broadcast_query = f"""
            SELECT COUNT(*) as count FROM {TABLES.BROADCAST_NOTIFICATIONS.value} bn
            LEFT JOIN {TABLES.USER_BROADCASTS.value} ub ON bn.id = ub.broadcast_id AND ub.user_id = $1
            WHERE (bn.target_role = 'all' OR bn.target_role = $2)
            AND (ub.is_read IS NULL OR ub.is_read = FALSE)
            AND bn.active = TRUE
        """
        broadcast_count = await db.fetch_one(broadcast_query, user_id, user_role)
        
        total = (personal_count['count'] if personal_count else 0) + (broadcast_count['count'] if broadcast_count else 0)
        
        return {"unread_count": total}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error counting unread notifications: {e}")
        raise HTTPException(status_code=500, detail="Error counting notifications")

@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(notification_id: int, authorization: Optional[str] = Header(None)):
    """
    Mark a personal notification as read.
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']

        # Verify ownership
        check_query = f"SELECT id FROM {TABLES.NOTIFICATIONS.value} WHERE id = $1 AND user_id = $2"
        existing = await db.fetch_one(check_query, notification_id, user_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Notification not found")

        update_query = f"""
            UPDATE {TABLES.NOTIFICATIONS.value} 
            SET is_read = TRUE 
            WHERE id = $1 
            RETURNING *
        """
        updated = await db.fetch_one(update_query, notification_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification: {e}")
        raise HTTPException(status_code=500, detail="Error updating notification")

# Broadcast endpoints

@router.get("/broadcasts", response_model=List[BroadcastNotificationResponse])
async def get_broadcasts(authorization: Optional[str] = Header(None)):
    """
    Get broadcast notifications visible to the user, including read status.
    Only returns ACTIVE broadcasts for normal users.
    """
    try:
        user = await get_current_web_user(authorization) # Ensure user is authenticated
        user_id = user['id']
        user_role = user.get('role', 'customer')

        # This query fetches active broadcasts relevant to the user's role
        # and includes their read status from the user_broadcasts table.
        query = f"""
            SELECT 
                bn.id,
                bn.created_at,
                bn.title,
                bn.message,
                bn.image_url,
                bn.link_url,
                bn.target_role,
                bn.active,
                COALESCE(ub.is_read, FALSE) as is_read
            FROM {TABLES.BROADCAST_NOTIFICATIONS.value} bn
            LEFT JOIN {TABLES.USER_BROADCASTS.value} ub ON bn.id = ub.broadcast_id AND ub.user_id = $1
            WHERE bn.active = TRUE AND (bn.target_role = 'all' OR bn.target_role = $2)
            ORDER BY bn.created_at DESC
        """
        broadcasts = await db.fetch_all(query, user_id, user_role)
        return [BroadcastNotificationResponse(**b) for b in broadcasts]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching broadcasts: {e}")
        raise HTTPException(status_code=500, detail="Error fetching broadcasts")

@router.get("/broadcasts/all", response_model=List[BroadcastNotificationResponse])
async def get_all_broadcasts(current_user: dict = Depends(require_admin)):
    """
    Admin: Get ALL broadcast notifications (Active + Drafts).
    """
    try:
        query = f"SELECT * FROM {TABLES.BROADCAST_NOTIFICATIONS.value} ORDER BY created_at DESC"
        broadcasts = await db.fetch_all(query)
        return [BroadcastNotificationResponse(**b) for b in broadcasts]
    except Exception as e:
        logger.error(f"Error fetching all broadcasts: {e}")
        raise HTTPException(status_code=500, detail="Error fetching all broadcasts")

@router.put("/broadcasts/{broadcast_id}/read")
async def mark_broadcast_read(broadcast_id: int, authorization: Optional[str] = Header(None)):
    """
    Mark a broadcast notification as read for the current user.
    """
    try:
        user = await get_current_web_user(authorization)
        user_id = user['id']

        # Upsert into user_broadcasts
        # If exists, update is_read. If not, insert.
        query = f"""
            INSERT INTO {TABLES.USER_BROADCASTS.value} (user_id, broadcast_id, is_read, sent_at)
            VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, broadcast_id) 
            DO UPDATE SET is_read = TRUE
            RETURNING *
        """
        # Note: We should verify broadcast exists first to be safe, but FK constraint handles validity.
        try:
            await db.fetch_one(query, user_id, broadcast_id)
        except Exception as e:
            # Likely FK violation if broadcast_id wrong
            logger.error(f"Error marking broadcast read: {e}")
            raise HTTPException(status_code=404, detail="Broadcast not found")
            
        return {"status": "success", "message": "Broadcast marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in mark_broadcast_read: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

# Admin/Internal endpoint to create notification (for testing or internal logic usage)
@router.post("/", response_model=NotificationResponse, dependencies=[Depends(require_admin)])
async def create_notification(notification: NotificationCreate): # Authenticated Admin
    """
    Internal/Admin: Create a notification for a user.
    """
    try:
        query = f"""
            INSERT INTO {TABLES.NOTIFICATIONS.value} 
            (user_id, order_id, type, title, message, image_url, link_url, is_read, email_sent)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        result = await db.fetch_one(
            query,
            notification.user_id,
            notification.order_id,
            notification.type,
            notification.title,
            notification.message,
            notification.image_url,
            notification.link_url,
            notification.is_read,
            notification.email_sent
        )
        return result
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/broadcasts", response_model=BroadcastNotificationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_broadcast(broadcast: BroadcastNotificationCreate):
    """
    Internal/Admin: Create a broadcast notification.
    """
    try:
        query = f"""
            INSERT INTO {TABLES.BROADCAST_NOTIFICATIONS.value} (title, message, image_url, link_url, target_role, active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at, title, message, image_url, link_url, target_role, active
        """
        
        row = await db.fetch_one(
            query, 
            broadcast.title, 
            broadcast.message, 
            broadcast.image_url, 
            broadcast.link_url, 
            broadcast.target_role,
            broadcast.active
        )
        
        return BroadcastNotificationResponse(**row)
        
    except Exception as e:
        logger.error(f"Error creating broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/broadcasts/{broadcast_id}", response_model=BroadcastNotificationResponse, dependencies=[Depends(require_admin)])
async def update_broadcast(broadcast_id: int, broadcast: BroadcastNotificationCreate):
    """
    Internal/Admin: Edit a broadcast notification (draft or active).
    """
    try:
        # Check if exists
        check_query = f"SELECT * FROM {TABLES.BROADCAST_NOTIFICATIONS.value} WHERE id = $1"
        existing = await db.fetch_one(check_query, broadcast_id)
        if not existing:
             raise HTTPException(status_code=404, detail="Broadcast not found")
             
        # Prevent editing if already active
        if existing['active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No se puede editar una notificación que ya ha sido publicada (active=True)."
            )

        query = f"""
            UPDATE {TABLES.BROADCAST_NOTIFICATIONS.value}
            SET title = $1,
                message = $2,
                image_url = $3,
                link_url = $4,
                target_role = $5,
                active = $6
            WHERE id = $7
            RETURNING id, created_at, title, message, image_url, link_url, target_role, active
        """
        
        row = await db.fetch_one(
            query,
            broadcast.title,
            broadcast.message,
            broadcast.image_url,
            broadcast.link_url,
            broadcast.target_role,
            broadcast.active,
            broadcast_id
        )
        
        return BroadcastNotificationResponse(**row)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating broadcast: {e}")
        raise HTTPException(status_code=500, detail="Error updating broadcast")


@router.post("/upload-image")
async def upload_promotion_image(image: NotificationImageUpload, current_user: dict = Depends(require_admin)):
    """
    Upload an image for a promotion/broadcast using Base64.
    Returns the URL to access the image.
    """
    try:
        # Decodificar la imagen base64
        # Extraer el header si existe (data:image/jpeg;base64,...)
        if "base64," in image.image_data:
            image_data = image.image_data.split("base64,")[1]
        else:
            image_data = image.image_data
            
        decoded_image = base64.b64decode(image_data)
        
        # Generar nombre único si no viene
        if not image.filename:
            ext = "jpg" # Default
            filename = f"{uuid.uuid4()}.{ext}"
        else:
            filename = f"{uuid.uuid4()}_{image.filename}"
            
        # Ruta donde se guardan las imagenes
        upload_dir = "/home/breightend/Tienda_Virtual_Backend_Mykonos/uploads/promotions"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as f:
            f.write(decoded_image)
            
        # URL publica para acceder a la imagen
        image_url = f"https://api.mykonosboutique.com.ar/uploads/promotions/{filename}"
        
        return {"image_url": image_url}
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al subir la imagen"
        )

@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_old_notifications(current_user: dict = Depends(require_admin)):
    """
    Elimina notificaciones y difusiones con más de 6 meses de antigüedad.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=180)
        
        # Eliminar notificaciones personales antiguas
        query_personal = f"DELETE FROM {TABLES.NOTIFICATIONS.value} WHERE created_at < $1"
        await db.execute(query_personal, cutoff_date)
        
        # Eliminar user_broadcasts asociados a broadcasts antiguos
        # Primero obtenemos los IDs para asegurar integridad si no hay cascade
        query_user_broadcasts = f"""
            DELETE FROM {TABLES.USER_BROADCASTS.value} 
            WHERE broadcast_id IN (
                SELECT id FROM {TABLES.BROADCAST_NOTIFICATIONS.value} 
                WHERE created_at < $1
            )
        """
        await db.execute(query_user_broadcasts, cutoff_date)
        
        # Eliminar broadcasts antiguos
        query_broadcasts = f"DELETE FROM {TABLES.BROADCAST_NOTIFICATIONS.value} WHERE created_at < $1"
        await db.execute(query_broadcasts, cutoff_date)
        
        logger.info(f"Cleanup executed. Notifications older than {cutoff_date} removed.")
        return {"message": "Limpieza de notificaciones antiguas completada con éxito."}
        
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al limpiar notificaciones antiguas"
        )
