from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from utils.nave_service import create_payment_preference

router = APIRouter(tags=["Nave Payments"])

class Amount(BaseModel):
    currency: str
    value: float

class Consumer(BaseModel):
    name: Optional[str] = "Consumidor Final"
    email: Optional[str] = "test@example.com"
    # Add other fields if necessary based on Nave docs, but these are common basics

class PaymentRequest(BaseModel):
    amount: Amount
    consumer: Optional[Consumer] = None
    # We might want to accept cart items too, but for payment creation, amount is critical.
    # Allowing extra fields to be passed through if needed.

@router.post("/create-payment")
async def create_payment(payment_request: PaymentRequest):
    """
    Creates a payment preference in Nave and returns the checkout URL.
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        payment_data = payment_request.dict(exclude_none=True)
        
        # If consumer wasn't provided, the service layer handles dummy data, 
        # or we can ensure it here. The model defaults handle it partially, 
        # but if consumer is None in request, payment_data['consumer'] won't exist.
        # Let's let the service layer fall back to dummy data if 'consumer' is missing.
        
        checkout_url = create_payment_preference(payment_data)
        return {"checkout_url": checkout_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
