import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=('settings_',)
    )
    
    # Application
    app_name: str = "PetalClone API"
    debug: bool = False
    
    # API Keys - will be loaded from environment variables
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None
    
    # Hyperbrowser.ai (for web scraping)
    hyperbrowser_api_key: Optional[str] = None
    
    # Supabase (for database)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Model configurations (renamed to avoid protected namespace)
    default_ai_model: str = "agentic"
    ai_model_configs: Dict[str, Dict[str, Any]] = {
        "agentic": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000
        },
        "fast": {
            "provider": "openai", 
            "model": "gpt-4o",
            "max_tokens": 4000
        },
        "precise": {
            "provider": "google",
            "model": "gemini-2.0-flash-exp",
            "max_tokens": 4000
        },
        "economic": {
            "provider": "openai",
            "model": "gpt-4o-mini", 
            "max_tokens": 4000
        }
    }


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def validate_api_keys():
    """Validate that required API keys are available"""
    missing_keys = []
    
    if not settings.anthropic_api_key:
        missing_keys.append("ANTHROPIC_API_KEY")
    
    if not settings.openai_api_key:
        missing_keys.append("OPENAI_API_KEY")
        
    if not settings.google_ai_api_key:
        missing_keys.append("GOOGLE_AI_API_KEY")
    
    if missing_keys:
        print(f"⚠️  Missing API keys: {', '.join(missing_keys)}")
        print("   Add them as environment variables or create a .env file")
        return False
    
    print("✅ All API keys configured successfully")
    return True 