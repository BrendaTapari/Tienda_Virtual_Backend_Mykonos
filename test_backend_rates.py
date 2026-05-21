import requests
import json

url = "http://localhost:8080/api/admin/shipping-config/rates"
payload = {
  "customerId": "0001195007",
  "postalCodeOrigin": "3100",
  "postalCodeDestination": "5000",
  "deliveredType": "D",
  "dimensions": {
    "weight": 500,
    "height": 10,
    "width": 20,
    "length": 30
  }
}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
