from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routes import chat, ingest, health
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Portfolio Assistant API",
    description="Multi-agent RAG system for portfolio exploration",
    version="1.0.0"
)

# Add CORS middleware
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

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Portfolio Assistant API started")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Supabase connected: {settings.SUPABASE_URL[:50]}...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Portfolio Assistant API shutdown")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
