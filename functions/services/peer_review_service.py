import time
import uuid
from api.providers.firebase import FirestoreRepository

code_reviews_repo = FirestoreRepository("codeReviews")
endorsements_repo = FirestoreRepository("skillEndorsements")

class PeerReviewService:
    """
    Peer Code Review & Skill Endorsements System Service.
    Allows verified students and mentors to submit inline code reviews and endorse developer skills.
    """

    @classmethod
    def submit_code_review(cls, project_id: str, reviewer_uid: str, reviewer_name: str, code_snippet: str, review_comment: str, rating: int = 5) -> dict:
        review_id = f"rev_{str(uuid.uuid4())[:8]}"
        review_doc = {
            "reviewId": review_id,
            "projectId": project_id,
            "reviewerUID": reviewer_uid,
            "reviewerName": reviewer_name,
            "codeSnippet": code_snippet,
            "reviewComment": review_comment,
            "rating": min(5, max(1, rating)),
            "createdAt": time.time()
        }
        code_reviews_repo.set(review_id, review_doc)
        return review_doc

    @classmethod
    def get_project_reviews(cls, project_id: str) -> list:
        return code_reviews_repo.query(filters=[("projectId", "==", project_id)])

    @classmethod
    def endorse_skill(cls, target_uid: str, endorser_uid: str, endorser_name: str, skill_name: str) -> dict:
        end_id = f"end_{str(uuid.uuid4())[:8]}"
        end_doc = {
            "endorsementId": end_id,
            "targetUID": target_uid,
            "endorserUID": endorser_uid,
            "endorserName": endorser_name,
            "skillName": skill_name,
            "createdAt": time.time()
        }
        endorsements_repo.set(end_id, end_doc)
        return end_doc

    @classmethod
    def get_student_endorsements(cls, target_uid: str) -> list:
        return endorsements_repo.query(filters=[("targetUID", "==", target_uid)])
