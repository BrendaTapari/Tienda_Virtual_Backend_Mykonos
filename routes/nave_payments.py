from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from utils.nave_service import create_payment_preference, check_payment_request_status, cancel_payment_request, cancel_payment

router = APIRouter(tags=["Nave Payments"])

class Amount(BaseModel):
    currency: str
    value: float

class Consumer(BaseModel):
    name: Optional[str] = "Consumidor Final"
    email: Optional[str] = "test@example.com"
    # Add other fields if necessary based on Nave docs, but these are common basics

class Item(BaseModel):
    name: str
    description: Optional[str] = "Item Description"
    quantity: int
    unit_price: float

class PaymentRequest(BaseModel):
    amount: Amount
    consumer: Optional[Consumer] = None
    items: Optional[list[Item]] = None
    external_payment_id: Optional[str] = None

@router.post("/create-payment")
async def create_payment(payment_request: PaymentRequest):
    """
    Creates a payment preference in Nave and returns the checkout URL.
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        payment_data = payment_request.dict(exclude_none=True)
        
        # If items are present, ensure unit_price is handled correctly by service (service expects it in structure)
        # The service layer handles the mapping from this dict to the Nave payload.
        
        result = create_payment_preference(payment_data)
        # result is now a dict { "checkout_url": ..., "payment_request_id": ... }
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{payment_request_id}")
async def get_payment_status(payment_request_id: str):
    """
    Checks the status of a payment intent by its ID on Nave/Ranty.
    If the status is SUCCESS_PROCESSED, it attempts to confirm the order if not already confirmed.
    """
    try:
        # 1. Get status from Nave
        status_data = check_payment_request_status(payment_request_id)
        
        # 2. Extract status name
        # JSON structure: "status": { "name": "SUCCESS_PROCESSED" }
        status_obj = status_data.get('status', {})
        if isinstance(status_obj, dict):
            status_name = status_obj.get('name', '').upper()
        else:
            status_name = str(status_obj).upper()
            
        # 3. If Successful, trigger confirmation (Idempotent)
        if status_name == 'SUCCESS_PROCESSED':
            external_id = status_data.get('external_payment_id')
            if external_id:
                # Extract Order ID
                order_id = None
                if "order-" in external_id:
                    try:
                        order_id = int(external_id.split("order-")[1])
                    except:
                        pass
                else:
                    try:
                        order_id = int(external_id)
                    except:
                        pass
                
                if order_id:
                    from utils.order_service import confirm_order_payment
                    # Trigger confirmation logic
                    # We use a try/except specifically for the confirmation part so we don't fail the status check
                    # if the order is already confirmed or something minor happens.
                    try:
                        await confirm_order_payment(
                            order_id=order_id, 
                            payment_reference=status_data.get('id', payment_request_id),
                            payment_method="Nave (Status Check)"
                        )
                    except HTTPException as exc:
                        # If 400/already processed, it's fine
                        pass
                    except Exception as e:
                        print(f"Error auto-confirming order {order_id} during status check: {e}")

        return status_data

    except Exception as e:
        # If it's a 404 from Nave or other error
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/payment-request/{payment_request_id}")
async def delete_payment_request(payment_request_id: str):
    """
    Cancels a payment request (intention) in Sandbox.
    Can only be cancelled if it hasn't been used yet.
    """
    try:
        result = cancel_payment_request(payment_request_id)
        return result
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        # Basic mapping of error messages to status codes
        if "Cancellation Failed" in error_msg:
             status_code = 400
        raise HTTPException(status_code=status_code, detail=error_msg)

@router.delete("/payment/{payment_id}")
async def delete_payment(payment_id: str):
    """
    Cancels an APPROVED payment in Sandbox.
    Returns status 'CANCELLING' initially.
    """
    try:
        result = cancel_payment(payment_id)
        return result
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        if "Payment Cancellation Error" in error_msg:
             status_code = 400 
        raise HTTPException(status_code=status_code, detail=error_msg)
