import time
import uuid
from api.providers.firebase import FirestoreRepository

roles_repo = FirestoreRepository("teamRoles")
applications_repo = FirestoreRepository("roleApplications")

class CollaborationService:
    """
    Project Collaboration Requests & Team Roles Service.
    Allows project owners to post open team roles and manage student application flows.
    """

    @classmethod
    def create_team_role(cls, project_id: str, owner_uid: str, role_title: str, required_skills: list, description: str) -> dict:
        role_id = f"role_{str(uuid.uuid4())[:8]}"
        role_doc = {
            "roleId": role_id,
            "projectId": project_id,
            "ownerUID": owner_uid,
            "roleTitle": role_title,
            "requiredSkills": required_skills,
            "description": description,
            "status": "open",
            "applicantCount": 0,
            "createdAt": time.time()
        }
        roles_repo.set(role_id, role_doc)
        return role_doc

    @classmethod
    def apply_for_role(cls, role_id: str, applicant_uid: str, cover_note: str) -> dict:
        role = roles_repo.get(role_id)
        if not role:
            raise Exception("Team role not found")

        app_id = f"app_{str(uuid.uuid4())[:8]}"
        app_doc = {
            "applicationId": app_id,
            "roleId": role_id,
            "projectId": role.get("projectId"),
            "ownerUID": role.get("ownerUID"),
            "applicantUID": applicant_uid,
            "coverNote": cover_note,
            "status": "pending",
            "createdAt": time.time()
        }
        applications_repo.set(app_id, app_doc)

        # Increment applicant count
        role["applicantCount"] = role.get("applicantCount", 0) + 1
        roles_repo.set(role_id, role)

        return app_doc

    @classmethod
    def get_project_roles(cls, project_id: str) -> list:
        return roles_repo.query(filters=[("projectId", "==", project_id)])
