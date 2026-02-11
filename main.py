"""
Main FastAPI application for Mykonos Backend.
Handles database lifecycle and route configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from routes import products, groups, user, purchases, contact
from config.db_connection import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



import asyncio
from utils.tasks import deactivate_expired_discounts
from utils.order_tasks import cancel_expired_orders
from utils.notification_tasks import cleanup_old_notifications_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize database connection pool
    logger.info("Starting up Mykonos API...")
    try:
        await DatabaseManager.initialize()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Continue anyway - the app will fail on first DB request
        
    # Start background cleanup tasks
    async def run_periodic_cleanup():
        while True:
            try:
                await deactivate_expired_discounts()
                # Run every hour (3600 seconds)
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discount cleanup task: {e}")
                await asyncio.sleep(60) # Retry after 1 min on error
    
    async def run_periodic_order_cancellation():
        while True:
            try:
                await cancel_expired_orders()
                # Run every 5 minutes (300 seconds)
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in order cancellation task: {e}")
                await asyncio.sleep(60) # Retry after 1 min on error

    async def run_periodic_notification_cleanup():
        while True:
            try:
                # Run cleanup on startup/every cycle
                await cleanup_old_notifications_task()
                # Run every week (604800 seconds)
                await asyncio.sleep(604800)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification cleanup task: {e}")
                await asyncio.sleep(3600) # Retry after 1 hour on error

    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    order_cancel_task = asyncio.create_task(run_periodic_order_cancellation())
    notification_cleanup_task = asyncio.create_task(run_periodic_notification_cleanup())
    
    logger.info("Background cleanup, order cancellation, and notification tasks started")
    
    yield
    
    # Shutdown
    # Cancel background tasks
    cleanup_task.cancel()
    order_cancel_task.cancel()
    notification_cleanup_task.cancel()
    try:
        await cleanup_task
        await order_cancel_task
        await notification_cleanup_task
    except asyncio.CancelledError:
        pass
        
    logger.info("Shutting down Mykonos API...")
    try:
        await DatabaseManager.close()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Mykonos API",
    description="Backend API for Mykonos Virtual Store",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "http://localhost:5173",
    "https://fastapi.mykonosboutique.com.ar",
    "https://api.mykonosboutique.com.ar",
    "https://mykonosboutique.com.ar"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/products", tags=["Productos"])
app.include_router(groups.router, prefix="/groups", tags=["Grupos"])
app.include_router(user.router, prefix="/auth", tags=["Autenticación"])
# Also include user router with /users prefix for compatibility
app.include_router(user.router, prefix="/users", tags=["Usuarios"])
app.include_router(purchases.router, prefix="/purchases", tags=["Compras"])
app.include_router(contact.router, prefix="/contact", tags=["Contacto"])

#branches
from routes import branch
app.include_router(branch.router, prefix="/branch", tags=["Sucursales"])

# Import and include admin router
from routes import admin
app.include_router(admin.router, prefix="/admin", tags=["Administración"])

# Import and include cart and orders routers
# Import and include cart and orders routers
from routes import cart, orders, notifications
app.include_router(cart.router, prefix="/cart", tags=["Carrito"])
app.include_router(orders.router, prefix="/orders", tags=["Órdenes"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notificaciones"])

# Import and include promotions router
from routes import promotions
app.include_router(promotions.router, prefix="/promotions", tags=["Promociones"])

# Import and include nave payments router
from routes import nave_payments
app.include_router(nave_payments.router, prefix="/api/nave", tags=["Pagos Nave"])

# Import and include payment webhooks (callbacks)
from routes import payment_webhooks
app.include_router(payment_webhooks.router, prefix="/api/payments", tags=["Webhooks Pagos"])

# Import and include waiting list router
from routes import waiting_list
app.include_router(waiting_list.router, prefix="/waiting-list", tags=["Lista de Espera"])

# Mount static files directory for product images
# Using shared directory that multiple backends access
images_dir = "/home/breightend/imagenes-productos"
if os.path.exists(images_dir):
    app.mount(
        "/static/productos",
        StaticFiles(directory=images_dir),
        name="productos"
    )
    # Also mount at legacy path for backward compatibility
    app.mount(
        "/imagenes-productos",
        StaticFiles(directory=images_dir),
        name="imagenes"
    )
    logger.info(f"Mounted static files directory: {images_dir}")
else:
    logger.warning(f"Images directory not found: {images_dir}")


@app.get("/")
async def home():
    """Root endpoint - health check."""
    return {
        "message": "API Mykonos funcionando correctamente",
        "version": "1.0.0",
        "status": "online"
    }

# Mount static files directory for promotions
promotions_dir = "/home/breightend/galeria_imagenes_mykonos/imagenes_promociones"
if os.path.exists(promotions_dir):
    app.mount(
        "/static/promociones",
        StaticFiles(directory=promotions_dir),
        name="promociones"
    )
    logger.info(f"Mounted static promotions directory: {promotions_dir}")
else:
    logger.warning(f"Promotions directory not found: {promotions_dir}")

# Mount static files directory for general assets (Logo, etc)
assets_dir = "/home/breightend/Tienda_Virtual_Backend_Mykonos/images"
if os.path.exists(assets_dir):
    app.mount(
        "/static/assets",
        StaticFiles(directory=assets_dir),
        name="assets"
    )
    logger.info(f"Mounted static assets directory: {assets_dir}")
else:
    logger.warning(f"Assets directory not found: {assets_dir}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Try to get the database pool to verify connection
        pool = await DatabaseManager.get_pool()
        db_status = "connected" if pool else "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status
    }