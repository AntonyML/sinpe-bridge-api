from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database (optional for development)
    DATABASE_URL: Optional[str] = None
    DEBUG: bool = True
    
    # API Security
    API_KEY: str = "dev-key-12345"
    API_KEY_HEADER: str = "x-api-key"
    
    # Request Handling
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    REQUEST_TIMEOUT_SECONDS: int = 30
    
    # SMS Processing
    SMS_CLOCK_SKEW_SECONDS: int = 300  # 5 minutes
    
    # HMAC Signing (for responses back to Android)
    HMAC_ALGORITHM: str = "sha256"
    HMAC_SECRET_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    STRUCTURED_LOGGING: bool = True
    
    # CORS
    CORS_ORIGINS: list = [
        "capacitor://localhost",
        "ionic://localhost",
        "file://",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    # Storage
    UPLOAD_STORAGE_PATH: str = "uploads"
    ENABLE_R2_STORAGE: bool = False  # Cloudflare R2
    R2_BUCKET_NAME: Optional[str] = None
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    
    # External Services
    NOTIFICATION_WEBHOOK_URL: Optional[str] = None
    POS_API_URL: Optional[str] = None
    
    # Observability
    ENABLE_METRICS: bool = True
    METRICS_EXPORT_INTERVAL: int = 60  # seconds
    
    # Feature Flags
    ENABLE_OCR_PIPELINE: bool = False
    ENABLE_FRAUD_DETECTION: bool = True
    ENABLE_SMS_ARCHIVAL: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

