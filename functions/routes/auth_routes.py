from fastapi import APIRouter, HTTPException, Depends
from models.schemas import StudentRegisterSchema, LoginSchema, OTPRequestSchema, OTPVerifySchema
from services.auth_service import AuthService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/register")
def register_info():
    return {
        "status": "active",
        "endpoint": "/api/v1/auth/register",
        "method": "POST",
        "message": "Student Registration API endpoint. Please send a POST request with registration details."
    }

@router.post("/register")
def register(schema: StudentRegisterSchema):
    try:
        return AuthService.register_student(schema)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/login")
def login_info():
    return {
        "status": "active",
        "endpoint": "/api/v1/auth/login",
        "method": "POST",
        "message": "Authentication API endpoint active. Submit a POST request with JSON body containing 'identifier' (Email or SPN) and 'password'."
    }

@router.post("/login")
def login(schema: LoginSchema):
    try:
        return AuthService.login(schema)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/otp/request")
def request_otp(schema: OTPRequestSchema):
    try:
        return AuthService.request_otp(schema.email, schema.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/otp/verify")
def verify_otp(schema: OTPVerifySchema):
    try:
        return AuthService.verify_otp(schema.email, schema.otp)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
def get_me(user: dict = Depends(require_authenticated_user)):
    return user

from pydantic import BaseModel

class ResetRequestSchema(BaseModel):
    identifier: str

class ResetConfirmSchema(BaseModel):
    identifier: str
    otp: str
    newPassword: str

@router.post("/forgot-password/request-otp")
def request_password_reset_otp(schema: ResetRequestSchema):
    try:
        return AuthService.request_password_reset_otp(schema.identifier)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/forgot-password/reset")
def reset_password(schema: ResetConfirmSchema):
    try:
        return AuthService.reset_password_with_otp(schema.identifier, schema.otp, schema.newPassword)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

