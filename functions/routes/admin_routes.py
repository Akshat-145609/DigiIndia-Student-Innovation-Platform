from fastapi import APIRouter, HTTPException, Depends
from models.schemas import AdminUserUpdateSchema
from services.admin_service import AdminService
from middleware.auth_middleware import require_admin_user

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/users")
def list_all_users(admin: dict = Depends(require_admin_user)):
    return AdminService.list_all_users()

@router.put("/users/status")
def update_user_status(schema: AdminUserUpdateSchema, admin: dict = Depends(require_admin_user)):
    try:
        return AdminService.update_user_status(schema.studentUID, schema.role, schema.verificationStatus, schema.status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{student_uid}")
def delete_user(student_uid: str, admin: dict = Depends(require_admin_user)):
    try:
        return AdminService.delete_user(student_uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/projects")
def list_all_projects(admin: dict = Depends(require_admin_user)):
    return AdminService.list_all_projects()

@router.put("/projects/{project_id}")
def update_project(project_id: str, status: str = None, verification_status: str = None, trust_score: int = None, admin: dict = Depends(require_admin_user)):
    try:
        return AdminService.update_project_status(project_id, status, verification_status, trust_score)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, admin: dict = Depends(require_admin_user)):
    try:
        return AdminService.delete_project(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/users")
def get_user_analytics(admin: dict = Depends(require_admin_user)):
    return AdminService.get_user_analytics()

@router.get("/analytics/api-usage")
def get_api_usage_analytics(admin: dict = Depends(require_admin_user)):
    return AdminService.get_api_usage_analytics()

@router.get("/models")
def get_training_models(admin: dict = Depends(require_admin_user)):
    return AdminService.get_training_models()

@router.put("/models/{model_id}")
def update_model_status(model_id: str, status: str = "active", admin: dict = Depends(require_admin_user)):
    return AdminService.update_model_status(model_id, status)
