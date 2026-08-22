import hashlib
import jwt
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from api.providers.firebase import FirebaseProvider, FirestoreRepository

security_bearer = HTTPBearer(auto_error=False)
keys_repo = FirestoreRepository("apiKeys")
students_repo = FirestoreRepository("students")

def get_current_user(request: Request, creds: HTTPAuthorizationCredentials = Security(security_bearer)):
    """
    Authenticate user via Firebase Bearer Token, JWT, or X-DigiIndia-Key header
    """
    # 1. Check Developer API Key header
    api_key_header = request.headers.get("X-DigiIndia-Key")
    if api_key_header:
        hashed = hashlib.sha256(api_key_header.encode()).hexdigest()
        keys = keys_repo.query(filters=[("hashedKey", "==", hashed), ("status", "==", "active")])
        if keys:
            key_data = keys[0]
            owner_uid = key_data.get("ownerUID")
            student = students_repo.get(owner_uid)
            if student:
                return {"uid": owner_uid, "email": student.get("email"), "role": student.get("role", "student"), "auth_type": "api_key", "permissions": key_data.get("permissions", [])}
        raise HTTPException(status_code=401, detail="API-1001: Invalid or revoked Developer API Key")

    # 2. Check Bearer Token
    if creds and creds.credentials:
        token = creds.credentials
        # Try Firebase ID Token
        firebase_user = FirebaseProvider.verify_id_token(token)
        if firebase_user:
            email = firebase_user.get("email")
            role = "admin" if email == settings.ADMIN_EMAIL else "student"
            return {"uid": firebase_user.get("uid"), "email": email, "role": role, "auth_type": "firebase"}

        # Try App JWT Secret
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return {"uid": payload.get("uid"), "email": payload.get("email"), "role": payload.get("role", "student"), "auth_type": "jwt"}
        except Exception:
            pass

    # If endpoint allows anonymous/public access or token missing
    return None

def require_authenticated_user(request: Request, user: dict = Security(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="API-1001: Authentication required")
    return user

def require_admin_user(request: Request, user: dict = Security(require_authenticated_user)):
    is_admin_email = user.get("email") and user.get("email").lower() == settings.ADMIN_EMAIL.lower()
    is_admin_role = user.get("role") == "admin"
    if not (is_admin_email or is_admin_role):
        raise HTTPException(status_code=403, detail="API-1002: Admin privileges required")
    return user
