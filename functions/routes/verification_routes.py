from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProjectVerifyRequestSchema
from services.verification_service import VerificationService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/verification", tags=["Verification"])

@router.post("/project/crawl")
def verify_project_crawl(schema: ProjectVerifyRequestSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return VerificationService.verify_project_ownership(schema.projectId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ocr/id-check")
def process_id_ocr(doc_type: str = "abc_id", file_data: str = "", user: dict = Depends(require_authenticated_user)):
    return VerificationService.process_identity_ocr(doc_type, file_data)
