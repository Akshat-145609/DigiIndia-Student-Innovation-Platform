from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProjectCreateSchema, ProjectUpdateSchema
from services.project_service import ProjectService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("")
def create_project(schema: ProjectCreateSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return ProjectService.create_project(user["uid"], schema)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my")
def list_my_projects(user: dict = Depends(require_authenticated_user)):
    return ProjectService.list_user_projects(user["uid"])

@router.get("/public")
def list_public_projects(limit: int = 50):
    return ProjectService.list_public_projects(limit)

@router.get("/urls")
def list_all_project_urls():
    return ProjectService.list_all_project_urls()

@router.get("/{project_id}")
def get_project_details(project_id: str):
    proj = ProjectService.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@router.put("/{project_id}")
def update_project(project_id: str, schema: ProjectUpdateSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return ProjectService.update_project(user["uid"], project_id, schema.dict(exclude_unset=True))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str, user: dict = Depends(require_authenticated_user)):
    try:
        return ProjectService.delete_project(user["uid"], project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

