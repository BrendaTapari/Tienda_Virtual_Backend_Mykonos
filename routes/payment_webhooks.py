from fastapi import APIRouter, HTTPException, Body, Request, BackgroundTasks
from pydantic import BaseModel
import logging
import asyncio
from utils.nave_service import check_payment_status
from utils.order_service import confirm_order_payment

# Configure router
router = APIRouter()
logger = logging.getLogger(__name__)

class NaveWebhookPayload(BaseModel):
    payment_id: str
    payment_check_url: str
    external_payment_id: str

async def process_webhook_payload(payload: NaveWebhookPayload, environment: str):
    """
    Shared logic for processing webhooks.
    """
    logger.info(f"NAVE WEBHOOK [{environment}]: Received payment update. Payload: {payload.dict()}")
    
    try:
        # 1. Verify payment status with Nave
        # Run blocking requests call in a thread
        loop = asyncio.get_running_loop()
        payment_details = await loop.run_in_executor(None, check_payment_status, payload.payment_check_url)
        
        logger.info(f"NAVE WEBHOOK [{environment}]: Verified details: {payment_details}")
        
        # 2. Check payment status
        # Status is nested: "status": { "name": "APPROVED", ... }
        status_obj = payment_details.get('status', {})
        if isinstance(status_obj, dict):
            status_name = status_obj.get('name', '').upper()
        else:
            # Fallback if it's just a string, though docs say object
            status_name = str(status_obj).upper()
            
        logger.info(f"NAVE WEBHOOK [{environment}]: Status Name: {status_name}")
        
        # 3. Extract Order ID
        external_id = payload.external_payment_id
        order_id = None
        
        # Extract ID if format is "order-123"
        if "order-" in external_id:
            try:
                order_id_str = external_id.split("order-")[1]
                order_id = int(order_id_str)
            except IndexError:
                 logger.error(f"Could not parse order ID from: {external_id}")
                 return
        else:
            try:
                order_id = int(external_id)
            except ValueError:
                logger.error(f"Invalid order ID format: {external_id}")
                return

        # 4. Handle specific statuses
        if status_name == 'APPROVED':
            # Payment confirmed
            await confirm_order_payment(
                order_id=order_id, 
                payment_reference=payload.payment_id,
                payment_method=f"Nave ({environment})"
            )
            logger.info(f"Order {order_id} successfully confirmed based on APPROVED status.")
            
        elif status_name in ['REJECTED', 'CANCELLED', 'REFUNDED']:
            # Log failure
            logger.warning(f"Payment for Order {order_id} was {status_name}. No action taken yet (auto-cancellation logic could go here).")
            
        else:
            logger.info(f"Payment status '{status_name}' ignored. Waiting for final status.")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # We catch exceptions to ensure we return 200 OK to Nave, so they stop retrying.

@router.post("/sandbox/webhook")
async def handle_sandbox_webhook(payload: NaveWebhookPayload, background_tasks: BackgroundTasks):
    """
    Endpoint for receiving Sandbox payment notifications from Nave.
    Responds with 200 OK immediately and processes in background.
    """
    background_tasks.add_task(process_webhook_payload, payload, "SANDBOX")
    return {"status": "success", "message": "Notification received"}

@router.post("/webhook")
async def handle_production_webhook(payload: NaveWebhookPayload, background_tasks: BackgroundTasks):
    """
    Endpoint for receiving Production payment notifications from Nave.
    Responds with 200 OK immediately and processes in background.
    """
    background_tasks.add_task(process_webhook_payload, payload, "PROD")
    return {"status": "success", "message": "Notification received"}
