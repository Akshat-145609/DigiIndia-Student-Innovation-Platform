from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from middleware.auth_middleware import require_authenticated_user
from services.comment_service import CommentService

router = APIRouter(prefix="/projects", tags=["Comments"])

class CreateCommentSchema(BaseModel):
    text: str
    parentCommentId: Optional[str] = ""

@router.get("/{project_id}/comments")
def get_comments(project_id: str):
    return CommentService.get_project_comments(project_id)

@router.post("/{project_id}/comments")
def post_comment(project_id: str, schema: CreateCommentSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return CommentService.add_comment(user["uid"], project_id, schema.text, schema.parentCommentId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/comments/{comment_id}/like")
def like_comment(comment_id: str):
    try:
        return CommentService.like_comment(comment_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
