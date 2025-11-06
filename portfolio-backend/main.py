import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, ingest, health, analytics, debug
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Portfolio Assistant API",
    description="Multi-agent RAG system with analytics",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(debug.router, prefix="/api", tags=["debug"])  # ADD


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Portfolio Assistant API v2 started")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)