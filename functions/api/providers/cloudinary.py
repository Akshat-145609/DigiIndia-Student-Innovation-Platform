import logging
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from config import settings

logger = logging.getLogger(__name__)

# Initialize Cloudinary SDK
if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )
    logger.info("Cloudinary client initialized.")

class CloudinaryProvider:
    @staticmethod
    def upload_file(file_content, folder: str = "general", public_id: str = None, access_mode: str = "public"):
        """Upload file content or base64 to Cloudinary"""
        if not settings.CLOUDINARY_API_KEY:
            logger.warning("Cloudinary keys missing. Returning fallback upload mock URL.")
            return {
                "url": f"https://res.cloudinary.com/demo/image/upload/{folder}/sample.jpg",
                "public_id": f"{folder}/{public_id or 'mock_sample'}"
            }
        try:
            options = {
                "folder": f"digiindia/{folder}",
                "resource_type": "auto"
            }
            if public_id:
                options["public_id"] = public_id
            if access_mode == "authenticated":
                options["type"] = "authenticated"

            result = cloudinary.uploader.upload(file_content, **options)
            return {
                "url": result.get("secure_url") or result.get("url"),
                "public_id": result.get("public_id"),
                "format": result.get("format"),
                "bytes": result.get("bytes")
            }
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            return {"error": str(e), "url": f"https://via.placeholder.com/400x200?text={folder}"}

    @staticmethod
    def generate_signed_url(public_id: str, expiration_seconds: int = 3600):
        """Generate temporary signed URL for authenticated private assets"""
        if not settings.CLOUDINARY_API_KEY:
            return f"https://res.cloudinary.com/demo/image/upload/{public_id}"
        try:
            url, _ = cloudinary.utils.cloudinary_url(
                public_id,
                sign_url=True,
                type="authenticated",
                expires_at=int(cloudinary.utils.now() + expiration_seconds)
            )
            return url
        except Exception as e:
            logger.error(f"Cloudinary signed URL error: {e}")
            return None
