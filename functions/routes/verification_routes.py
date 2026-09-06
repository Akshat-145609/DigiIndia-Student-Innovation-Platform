from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import Optional
from models.schemas import ProjectVerifyRequestSchema
from services.verification_service import VerificationService
from middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/verification", tags=["Verification"])

@router.get("/project/crawl")
def verify_project_crawl_get(projectId: Optional[str] = Query(None, description="Project ID to verify and audit")):
    """
    GET /api/v1/verification/project/crawl
    Returns active crawler status or executes audit if projectId query param is provided
    """
    if not projectId:
        return {
            "status": "active",
            "endpoint": "/api/v1/verification/project/crawl",
            "methods": ["GET", "POST"],
            "message": "DigiBot Runtime SEO & Meta-Tag Verification Gateway is operational. Pass ?projectId=<id> or POST JSON payload to audit project."
        }
    try:
        return VerificationService.verify_project_ownership(projectId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/project/crawl")
async def verify_project_crawl_post(request: Request, projectId: Optional[str] = None):
    """
    POST /api/v1/verification/project/crawl
    Executes deep runtime SEO & Meta-Tag verification crawl for project
    """
    proj_id = projectId
    if not proj_id:
        try:
            body = await request.json()
            proj_id = body.get("projectId") or body.get("id")
        except Exception:
            pass

    if not proj_id:
        raise HTTPException(status_code=400, detail="projectId is required in JSON body ({'projectId': '...'}) or query parameter")

    try:
        return VerificationService.verify_project_ownership(proj_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ocr/id-check")
def process_id_ocr(doc_type: str = "abc_id", file_data: str = "", user: dict = Depends(get_current_user)):
    return VerificationService.process_identity_ocr(doc_type, file_data)
