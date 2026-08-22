import time
import uuid
import secrets
import httpx
from bs4 import BeautifulSoup
from api.providers.firebase import FirestoreRepository
from api.router import AIRouter
from models.schemas import ProjectCreateSchema

projects_repo = FirestoreRepository("projects")
metadata_repo = FirestoreRepository("projectMetadata")
verifications_repo = FirestoreRepository("projectVerification")

class ProjectService:

    @classmethod
    def create_project(cls, owner_uid: str, schema: ProjectCreateSchema):
        # 1. Duplicate Project Prevention Check
        existing_user_projects = cls.list_user_projects(owner_uid)
        for ep in existing_user_projects:
            if schema.repositoryURL and ep.get("repositoryURL", "").strip().lower() == schema.repositoryURL.strip().lower():
                raise Exception("A project with this Repository URL already exists in your portfolio.")
            if schema.liveURL and ep.get("liveURL", "").strip().lower() == schema.liveURL.strip().lower():
                raise Exception("A project with this Live URL already exists in your portfolio.")
            if ep.get("title", "").strip().lower() == schema.title.strip().lower():
                raise Exception("A project with this exact Title already exists in your portfolio.")

        project_id = str(uuid.uuid4())
        verification_token = secrets.token_urlsafe(16)

        # Basic HTTP metadata extraction
        extracted_meta = cls._extract_metadata(schema.liveURL or schema.repositoryURL)

        # AI Repository Analysis via AIRouter (Gemini/Grok/OpenAI)
        ai_analysis = AIRouter.analyze_repository(schema.repositoryURL, extracted_meta.get("description", ""))


        project_doc = {
            "projectId": project_id,
            "ownerUID": owner_uid,
            "title": schema.title,
            "description": schema.description,
            "repositoryURL": schema.repositoryURL,
            "liveURL": schema.liveURL or "",
            "visibility": schema.visibility or "public",
            "technologyStack": schema.technologyStack or [],
            "category": schema.category or "Software",
            "license": schema.license or "MIT",
            "tags": schema.tags or [],
            "verificationStatus": "pending",
            "status": "active",
            "trustScore": 40 + ai_analysis.get("trustScoreBonus", 10),
            "createdAt": time.time(),
            "updatedAt": time.time(),
            "lastScan": time.time()
        }
        projects_repo.set(project_id, project_doc)

        metadata_repo.set(project_id, {
            "projectId": project_id,
            "canonical": extracted_meta.get("canonical", schema.liveURL),
            "openGraph": extracted_meta.get("openGraph", {}),
            "aiSummary": ai_analysis.get("summary", ""),
            "lastCrawled": time.time()
        })

        verifications_repo.set(project_id, {
            "projectId": project_id,
            "verificationToken": verification_token,
            "verificationMethod": "meta_tag",
            "verificationStatus": "pending",
            "metaTag": f'<meta name="digiindia-student-innovation-platform" content="{verification_token}">',
            "attemptCount": 0,
            "createdAt": time.time()
        })

        # Send automated project upload confirmation email via Brevo
        try:
            from api.providers.brevo import BrevoEmailProvider
            from api.providers.firebase import FirestoreRepository
            students_repo = FirestoreRepository("students")
            profiles_repo = FirestoreRepository("profiles")
            st = students_repo.get(owner_uid) or {}
            prof = profiles_repo.get(owner_uid) or {}
            if st.get("email"):
                BrevoEmailProvider.send_project_upload_email(
                    recipient_email=st.get("email"),
                    recipient_name=prof.get("fullName", "Student Developer"),
                    project_title=schema.title,
                    project_id=project_id,
                    verification_token=verification_token
                )
        except Exception:
            pass

        return {
            "project": project_doc,
            "verification": {
                "verificationToken": verification_token,
                "metaTagHtml": f'<meta name="digiindia-student-innovation-platform" content="{verification_token}">'
            }
        }


    @staticmethod
    def get_project(project_id: str):
        proj = projects_repo.get(project_id)
        if not proj:
            return None
        meta = metadata_repo.get(project_id) or {}
        verif = verifications_repo.get(project_id) or {}
        return {"project": proj, "metadata": meta, "verification": verif}

    @staticmethod
    def list_user_projects(owner_uid: str):
        return projects_repo.query(filters=[("ownerUID", "==", owner_uid)])

    @staticmethod
    def list_public_projects(limit: int = 50):
        return projects_repo.query(filters=[("visibility", "==", "public")], limit=limit)

    @staticmethod
    def update_project(owner_uid: str, project_id: str, update_data: dict):
        proj = projects_repo.get(project_id)
        if not proj or proj.get("ownerUID") != owner_uid:
            raise Exception("Project not found or unauthorized")
        for key, val in update_data.items():
            if val is not None:
                proj[key] = val
        proj["updatedAt"] = time.time()
        projects_repo.set(project_id, proj)
        return proj

    @staticmethod
    def delete_project(owner_uid: str, project_id: str):
        proj = projects_repo.get(project_id)
        if not proj or proj.get("ownerUID") != owner_uid:
            raise Exception("Project not found or unauthorized")
        projects_repo.delete(project_id)
        metadata_repo.delete(project_id)
        verifications_repo.delete(project_id)
        return {"message": "Project deleted successfully", "projectId": project_id}

    @staticmethod
    def list_all_project_urls():
        projects = projects_repo.query(limit=500)
        urls = []
        for p in projects:
            if p.get("liveURL"):
                urls.append({"projectId": p.get("projectId"), "title": p.get("title"), "url": p.get("liveURL"), "type": "live"})
            if p.get("repositoryURL"):
                urls.append({"projectId": p.get("projectId"), "title": p.get("title"), "url": p.get("repositoryURL"), "type": "repository"})
        return urls

    @staticmethod
    def _extract_metadata(url: str) -> dict:
        if not url or not url.startswith("http"):
            return {}
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    title = soup.title.string if soup.title else ""
                    desc = ""
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    if meta_desc:
                        desc = meta_desc.get("content", "")
                    return {"title": title, "description": desc, "canonical": url}
        except Exception:
            pass
        return {"title": "", "description": "", "canonical": url}

