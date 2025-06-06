from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv

from .routers import clone
from .core.config import settings, validate_api_keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("🌸 PetalClone API starting up...")
    
    # Load environment variables
    load_dotenv()
    
    # Validate API keys (non-blocking - will warn if missing)
    print("🔑 Checking API keys...")
    api_keys_valid = validate_api_keys()
    
    if not api_keys_valid:
        print("⚠️  Some API keys are missing. Add them to use real LLM providers.")
        print("   The app will still work with mock data for testing.")
    
    yield
    
    # Shutdown logic
    print("🌸 PetalClone API shutting down...")


# Create FastAPI instance
app = FastAPI(
    title="PetalClone API",
    description="AI-powered website cloning with agentic architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clone.router, prefix="/api/v1", tags=["clone"])


@app.get("/")
async def root():
    return {
        "message": "🌸 Welcome to PetalClone API",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.0",
        "features": {
            "real_llm_apis": bool(settings.anthropic_api_key and settings.openai_api_key),
            "agentic_architecture": True,
            "supported_models": list(settings.ai_model_configs.keys())
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "petalclone-api",
        "version": "1.0.0",
        "api_keys_configured": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "google": bool(settings.google_ai_api_key)
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
