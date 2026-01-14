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
        
        checkout_url = create_payment_preference(payment_data)
        return {"checkout_url": checkout_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
