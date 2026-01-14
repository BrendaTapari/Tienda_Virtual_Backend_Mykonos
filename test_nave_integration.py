import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.nave_service import get_nave_token, create_payment_preference

def test_full_integration():
    print("=== TEST DE INTEGRACIÓN CON NAVE ===")
    
    # 1. Test Authentication
    print("\n1. Probando Autenticación (Obtener Token)...")
    try:
        token = get_nave_token()
        print(f"✅ Token obtenido exitosamente!")
        print(f"Token (primeros 20 chars): {token[:20]}...")
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return

    # 2. Test Payment Creation
    print("\n2. Probando Creación de Pago...")
    
    payment_data = {
        "amount": {
            "currency": "ARS",
            "value": 1500.0
        },
        "consumer": {
            "name": "Test Integration User",
            "email": "test@example.com",
            "doc_type": "DNI", 
            "doc_number": "11111111"
        },
        "items": [
            {
                "name": "Producto de Prueba",
                "description": "Test de integración",
                "quantity": 1,
                "unit_price": 1500.0
            }
        ],
        "external_payment_id": f"test_int_{os.urandom(4).hex()}"
    }

    try:
        checkout_url = create_payment_preference(payment_data)
        print(f"✅ Pago creado exitosamente!")
        print(f"Checkout URL: {checkout_url}")
    except Exception as e:
        print(f"❌ Error creando pago: {e}")

if __name__ == "__main__":
    test_full_integration()