import asyncio
import os
import logging
from dotenv import load_dotenv
from utils.paqar_servides import PaqarClient, RateRequestDTO

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

async def main():
    try:
        customer_id = os.getenv('MICORREO_CUSTOMER_ID', '12345')
        
        dto = RateRequestDTO(
            customerId=customer_id,
            postalCodeOrigin="1000",
            postalCodeDestination="1000",
            deliveredType="D",
            dimensions={"weight": 300, "height": 5, "width": 20, "length": 30}
        )
        async with PaqarClient() as client:
            rates = await client.get_rates(dto)
            print("\n--- RESULTS 1000 to 1000 ---")
            import json
            print(json.dumps(rates, indent=2))
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
