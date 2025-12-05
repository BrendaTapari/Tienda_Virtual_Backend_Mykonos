from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import products 

app = FastAPI()

origins = ["http://localhost:5173", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/products", tags=["Productos"])


@app.get("/")
def home():
    return {"message": "API Mykonos funcionando correctamente"}