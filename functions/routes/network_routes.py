from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from models.schemas import ConnectionRequestSchema
from services.network_service import NetworkService
from services.matchmaking_service import MatchmakingEngine
from services.collaboration_service import CollaborationService
from services.git_integration_service import GitIntegrationService
from services.peer_review_service import PeerReviewService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/network", tags=["Network Collaboration"])

class CreateRoleSchema(BaseModel):
    projectId: str
    roleTitle: str
    requiredSkills: List[str]
    description: str

class ApplyRoleSchema(BaseModel):
    roleId: str
    coverNote: str

class CodeReviewSchema(BaseModel):
    codeSnippet: str
    reviewComment: str
    rating: Optional[int] = 5

class EndorseSchema(BaseModel):
    skillName: str

@router.post("/follow/{following_uid}")
def follow_user(following_uid: str, user: dict = Depends(require_authenticated_user)):
    try:
        return NetworkService.follow_user(user["uid"], following_uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/follow/{following_uid}")
def unfollow_user(following_uid: str, user: dict = Depends(require_authenticated_user)):
    return NetworkService.unfollow_user(user["uid"], following_uid)

@router.post("/connection/request")
def send_connection_request(schema: ConnectionRequestSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return NetworkService.send_connection_request(user["uid"], schema.targetUID, schema.message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/connection/withdraw/{target_uid}")
def withdraw_connection_request(target_uid: str, user: dict = Depends(require_authenticated_user)):
    try:
        return NetworkService.withdraw_connection_request(user["uid"], target_uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/connection/disconnect/{target_uid}")
def disconnect_users(target_uid: str, user: dict = Depends(require_authenticated_user)):
    try:
        return NetworkService.disconnect_users(user["uid"], target_uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/{target_uid}")
def get_connection_status(target_uid: str, user: dict = Depends(require_authenticated_user)):
    return NetworkService.get_connection_status(user["uid"], target_uid)

@router.post("/connection/respond/{request_id}")
def respond_connection_request(request_id: str, accept: bool = True, user: dict = Depends(require_authenticated_user)):
    try:
        return NetworkService.respond_connection_request(user["uid"], request_id, accept)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my")
def get_my_network(user: dict = Depends(require_authenticated_user)):
    return NetworkService.list_network(user["uid"])

@router.get("/suggestions")
def get_ai_suggestions(user: dict = Depends(require_authenticated_user)):
    return NetworkService.get_ai_connection_suggestions(user["uid"])

@router.get("/matchmaking")
def get_student_matchmaking(user: dict = Depends(require_authenticated_user)):
    return MatchmakingEngine.match_students(user["uid"])

@router.post("/team-roles")
def create_team_role(schema: CreateRoleSchema, user: dict = Depends(require_authenticated_user)):
    return CollaborationService.create_team_role(schema.projectId, user["uid"], schema.roleTitle, schema.requiredSkills, schema.description)

@router.post("/team-roles/apply")
def apply_for_role(schema: ApplyRoleSchema, user: dict = Depends(require_authenticated_user)):
    return CollaborationService.apply_for_role(schema.roleId, user["uid"], schema.coverNote)

@router.get("/git-activity/{project_id}")
def get_git_activity(project_id: str):
    return GitIntegrationService.get_project_git_activity(project_id)

@router.post("/code-reviews/{project_id}")
def submit_code_review(project_id: str, schema: CodeReviewSchema, user: dict = Depends(require_authenticated_user)):
    return PeerReviewService.submit_code_review(project_id, user["uid"], user.get("email", "Student"), schema.codeSnippet, schema.reviewComment, schema.rating or 5)

@router.post("/endorse/{target_uid}")
def endorse_skill(target_uid: str, schema: EndorseSchema, user: dict = Depends(require_authenticated_user)):
    return PeerReviewService.endorse_skill(target_uid, user["uid"], user.get("email", "Student"), schema.skillName)
