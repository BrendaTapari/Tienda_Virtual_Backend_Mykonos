"""
Main FastAPI application for Mykonos Backend.
Handles database lifecycle and route configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from routes import products
from config.db_connection import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    
    yield
    
    # Shutdown: Close database connection pool
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
origins = ["http://localhost:5173", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/products", tags=["Productos"])


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