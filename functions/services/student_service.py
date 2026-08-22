import time
from api.providers.firebase import FirestoreRepository

students_repo = FirestoreRepository("students")
profiles_repo = FirestoreRepository("profiles")
projects_repo = FirestoreRepository("projects")
followers_repo = FirestoreRepository("followers")

class StudentService:

    @staticmethod
    def get_student_profile(uid: str):
        student = students_repo.get(uid)
        profile = profiles_repo.get(uid) or {}
        if not student:
            return None
        
        # Calculate fresh trust score
        trust_score = StudentService.calculate_trust_score(uid)
        profile["trustScore"] = trust_score

        return {
            "uid": student.get("uid"),
            "spn": student.get("spn"),
            "email": student.get("email"),
            "phone": student.get("phone"),
            "role": student.get("role", "student"),
            "status": student.get("status", "active"),
            "verificationStatus": student.get("verificationStatus", "pending"),
            "profile": profile
        }

    @staticmethod
    def update_profile(uid: str, update_data: dict):
        profile = profiles_repo.get(uid) or {}
        for key, val in update_data.items():
            if val is not None:
                profile[key] = val
        profile["updatedAt"] = time.time()
        profiles_repo.set(uid, profile)
        return profile

    @staticmethod
    def calculate_trust_score(uid: str) -> int:
        score = 20 # Base registration score
        profile = profiles_repo.get(uid) or {}
        student = students_repo.get(uid) or {}

        if student.get("verificationStatus") == "verified":
            score += 30
        
        if profile.get("bio"):
            score += 5
        if profile.get("skills") and len(profile.get("skills")) > 0:
            score += 10
        if profile.get("socialLinks"):
            score += 10
        
        # Check verified projects
        projects = projects_repo.query(filters=[("ownerUID", "==", uid)])
        for proj in projects:
            if proj.get("verificationStatus") == "verified":
                score += 15

        # Followers bonus
        followers = followers_repo.query(filters=[("followingUID", "==", uid)])
        score += min(len(followers) * 2, 10)

        return min(score, 100)
