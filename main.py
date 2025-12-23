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
        
    # Start background cleanup task
    async def run_periodic_cleanup():
        while True:
            try:
                await deactivate_expired_discounts()
                # Run every hour (3600 seconds)
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60) # Retry after 1 min on error

    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    logger.info("Background cleanup task started")
    
    yield
    
    # Shutdown
    # Cancel background task
    cleanup_task.cancel()
    try:
        await cleanup_task
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
    "https://mykonosboutique.com.ar",
    "*"
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
app.include_router(purchases.router, prefix="/purchases", tags=["Compras"])
app.include_router(contact.router, prefix="/contact", tags=["Contacto"])

#branches
from routes import branch
app.include_router(branch.router, prefix="/branch", tags=["Sucursales"])

# Import and include admin router
from routes import admin
app.include_router(admin.router, prefix="/admin", tags=["Administración"])

# Import and include cart and orders routers
from routes import cart, orders
app.include_router(cart.router, prefix="/cart", tags=["Carrito"])
app.include_router(orders.router, prefix="/orders", tags=["Órdenes"])

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