from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProfileUpdateSchema
from services.student_service import StudentService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/profile/me")
@router.get("/me")
def get_my_profile(user: dict = Depends(require_authenticated_user)):
    profile = StudentService.get_student_profile(user["uid"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/profile/{uid}")
def get_student_profile(uid: str):
    profile = StudentService.get_student_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.get("/profile/spn/{spn}")
def get_student_profile_by_spn(spn: str):
    profile = StudentService.get_student_profile_by_spn(spn)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/profile/me")
@router.put("/me")
def update_my_profile(schema: ProfileUpdateSchema, user: dict = Depends(require_authenticated_user)):
    return StudentService.update_profile(user["uid"], schema.dict(exclude_unset=True))

