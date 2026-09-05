from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from models.schemas import AIReviewRequestSchema
from services.ai_service import AIService
from services.plagiarism_service import PlagiarismAuditor
from services.dependency_tagger_service import DependencyTaggerService
from services.copilot_scanner_service import CoPilotBugScanner
from services.sandbox_service import SandboxEngine
from middleware.auth_middleware import require_authenticated_user
from api.providers.firebase import FirestoreRepository

router = APIRouter(prefix="/ai", tags=["AI Engine Workspace"])
knowledge_repo = FirestoreRepository("aiKnowledge")

class PlagiarismSchema(BaseModel):
    projectId: Optional[str] = ""
    codeSnippet: Optional[str] = ""

class TagDependenciesSchema(BaseModel):
    filename: str
    content: str

class BugScanSchema(BaseModel):
    codeContent: str
    filename: Optional[str] = "main.py"

class SandboxSchema(BaseModel):
    htmlCode: Optional[str] = ""
    cssCode: Optional[str] = ""
    jsCode: Optional[str] = ""

class TrainUrlSchema(BaseModel):
    url: str

class UploadMdSchema(BaseModel):
    title: str
    content: str

class GenerateKeySchema(BaseModel):
    label: Optional[str] = "Default API Key"


@router.post("/review/project/{project_id}")
def review_project(project_id: str, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.review_project(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/review/code")
def review_code(schema: AIReviewRequestSchema, user: dict = Depends(require_authenticated_user)):
    if not schema.codeSnippet:
        raise HTTPException(status_code=400, detail="codeSnippet required")
    return AIService.review_code_snippet(schema.codeSnippet, schema.language or "python")

@router.get("/assistant")
def get_assistant_status(q: Optional[str] = ""):
    return {
        "status": "online",
        "service": "DigiIndia AI Assistant Engine",
        "model": "Gemini 1.5 Flash + DigiIndia Knowledge Agent",
        "message": "DigiIndia AI Assistant Engine is ready. Send POST with { prompt } to query.",
        "query": q
    }

@router.post("/assistant")
def ask_assistant(schema: AIReviewRequestSchema):
    if not schema.prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    return AIService.ask_ai_assistant(schema.prompt, schema.codeSnippet or "")

@router.post("/analyze-url")
def analyze_url(url: str, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.analyze_url(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze-seo")
def analyze_seo(url: str, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.analyze_seo(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze-score/{project_id}")
def analyze_score(project_id: str, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.analyze_score(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze-ownership-url")
def analyze_ownership_url(url: str, verification_token: str = "", user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.analyze_ownership_url(url, verification_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/plagiarism-audit")
def audit_plagiarism(schema: PlagiarismSchema):
    return PlagiarismAuditor.audit_project_originality(schema.projectId, schema.codeSnippet)

@router.post("/tag-dependencies")
def tag_dependencies(schema: TagDependenciesSchema):
    return DependencyTaggerService.tag_manifest_content(schema.filename, schema.content)

@router.post("/bug-scan")
def bug_scan(schema: BugScanSchema):
    return CoPilotBugScanner.scan_code(schema.codeContent, schema.filename or "main.py")

@router.post("/sandbox/preview")
def sandbox_preview(schema: SandboxSchema):
    return SandboxEngine.generate_sandbox_bundle(schema.htmlCode, schema.cssCode, schema.jsCode)

@router.get("/validate-person-schema")
def validate_person_schema(user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.validate_person_schema(user["uid"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verification-status-ln")
def verification_status_ln(url: str, verification_token: str = ""):
    try:
        return AIService.get_verification_status_with_linenumber(url, verification_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/train-url")
def train_url(schema: TrainUrlSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.train_ai_model_from_url(schema.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-md")
def upload_md(schema: UploadMdSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.upload_md_training_file(schema.title, schema.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate-key")
def generate_key(schema: GenerateKeySchema, user: dict = Depends(require_authenticated_user)):
    try:
        return AIService.generate_user_api_key(user["uid"], schema.label)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/knowledge/{knowledge_id}")
def get_knowledge(knowledge_id: str):
    rec = knowledge_repo.get(knowledge_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Knowledge record not found")
    return rec
