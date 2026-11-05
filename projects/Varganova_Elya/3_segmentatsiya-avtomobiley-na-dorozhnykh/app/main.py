from fastapi import FastAPI
from app.api.routes import router
from app.db.database import Base, engine
from app.core.config import settings

app = FastAPI(title="Traffic Segmentation API", version="1.0.0")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "model": settings.model_name}
