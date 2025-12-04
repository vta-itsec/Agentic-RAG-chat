"""
Application Configuration

Centralized configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Enterprise RAG Chat"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3080"],
        env="CORS_ORIGINS"
    )
    
    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    JWT_REFRESH_SECRET: str = Field(..., env="JWT_REFRESH_SECRET")
    JWT_REFRESH_EXPIRATION_DAYS: int = 30
    
    # Database
    MONGO_URI: str = Field(..., env="MONGO_URI")
    POSTGRES_URL: Optional[str] = Field(None, env="POSTGRES_URL")
    
    # Vector Store
    QDRANT_URL: str = Field(default="http://qdrant:6333", env="QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = Field(None, env="QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME: str = "enterprise_documents"
    
    # Embeddings
    OLLAMA_BASE_URL: str = Field(
        default="http://ollama:11434", 
        env="OLLAMA_BASE_URL"
    )
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768
    
    # LLM Providers
    DEEPSEEK_API_KEY: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "docx", "txt", "md", "csv"]
    )
    UPLOAD_DIR: str = "/tmp/uploads"
    
    # Redis (for caching & rate limiting)
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
