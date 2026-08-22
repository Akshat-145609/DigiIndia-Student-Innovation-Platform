import os
from dotenv import load_dotenv

# Load environment variables from .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "DigiIndia")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5500")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "default_secret_key_digi_india")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    PORT: int = int(os.getenv("PORT", "8000"))

    # Admin
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Super Administrator")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "its.akshatnetworkhub23@gmail.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@987")

    # Firebase Client
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    FIREBASE_MESSAGING_SENDER_ID: str = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "")
    FIREBASE_APP_ID: str = os.getenv("FIREBASE_APP_ID", "")

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    # Brevo Email API
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "DigiIndia-StudentInnovationPlatform")
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "akshatpsd2005@gmail.com")
    OTP_EXPIRY_MINUTES: int = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))

    # AI Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROK_API_KEY: str = os.getenv("GROK_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Security
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    PASSWORD_PEPPER: str = os.getenv("PASSWORD_PEPPER", "")
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5500")

    # Feature Flags
    ENABLE_AI: bool = os.getenv("ENABLE_AI", "true").lower() == "true"
    ENABLE_EMAIL: bool = os.getenv("ENABLE_EMAIL", "true").lower() == "true"
    ENABLE_ANALYTICS: bool = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_NOTIFICATIONS: bool = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true"

settings = Settings()
