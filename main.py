from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes import router
from service import database  

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    database.inicializar_banco()
    yield

app = FastAPI(title="🍕🛵 Delivery RESTAURANTE - API", lifespan=lifespan)

app.include_router(router)

@app.get("/")
def home():
    return {"status": "Servidor Rodando! Acesse /docs para testar as rotas."}

