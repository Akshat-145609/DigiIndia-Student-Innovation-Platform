from fastapi import APIRouter, HTTPException, Depends
from models.schemas import APIKeyCreateSchema
from services.api_key_service import APIKeyService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/developer/keys", tags=["Developer API Keys"])

@router.post("")
def generate_api_key(schema: APIKeyCreateSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return APIKeyService.generate_api_key(user["uid"], schema)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("")
def list_my_api_keys(user: dict = Depends(require_authenticated_user)):
    return APIKeyService.list_user_keys(user["uid"])

@router.delete("/{key_id}")
def revoke_api_key(key_id: str, user: dict = Depends(require_authenticated_user)):
    try:
        return APIKeyService.revoke_key(user["uid"], key_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
