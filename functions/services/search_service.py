from api.providers.firebase import FirestoreRepository
from services.vector_search_service import VectorSearchEngine

projects_repo = FirestoreRepository("projects")
profiles_repo = FirestoreRepository("profiles")

KNOWN_TECH_DICTIONARY = [
    "Python", "FastAPI", "JavaScript", "React", "Node.js", "Firebase",
    "HTML5", "CSS3", "C++", "Java", "Rust", "Go", "TypeScript",
    "Machine Learning", "Artificial Intelligence", "Docker", "Kubernetes",
    "PostgreSQL", "MongoDB", "TailwindCSS", "Bootstrap", "Flutter"
]

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

class SearchService:

    @staticmethod
    def search_projects(
        query: str = "",
        technology: str = "",
        institution: str = "",
        verified_only: bool = False,
        language: str = "",
        license_type: str = "",
        min_stars: int = 0,
        min_trust_score: int = 0,
        country: str = "",
        sort_by: str = "relevance"
    ):
        projects = projects_repo.query(filters=[("visibility", "==", "public")], limit=200)
        results = []

        q_lower = query.lower().strip() if query else ""
        tech_lower = (technology or language).lower().strip() if (technology or language) else ""
        license_lower = license_type.lower().strip() if license_type else ""
        country_lower = country.lower().strip() if country else ""

        for p in projects:
            if verified_only and p.get("verificationStatus") != "verified":
                continue

            if min_trust_score > 0 and p.get("trustScore", 40) < min_trust_score:
                continue

            if min_stars > 0 and p.get("stargazersCount", 0) < min_stars:
                continue

            if license_lower and license_lower not in p.get("license", "").lower():
                continue

            if country_lower and country_lower != "global" and country_lower not in p.get("country", "global").lower():
                continue

            match = True
            if q_lower:
                in_title = q_lower in p.get("title", "").lower()
                in_desc = q_lower in p.get("description", "").lower()
                in_tags = any(q_lower in t.lower() for t in p.get("tags", []))
                in_tech = any(q_lower in t.lower() for t in p.get("technologyStack", []))
                if not (in_title or in_desc or in_tags or in_tech):
                    match = False

            if tech_lower:
                tech_stack = [t.lower() for t in p.get("technologyStack", [])]
                if not any(tech_lower in t for t in tech_stack):
                    match = False

            if match:
                results.append(p)

        # Sorting logic
        if sort_by == "trust_score":
            results.sort(key=lambda x: x.get("trustScore", 0), reverse=True)
        elif sort_by == "stars":
            results.sort(key=lambda x: x.get("stargazersCount", 0), reverse=True)
        elif sort_by == "date":
            results.sort(key=lambda x: x.get("createdAt", 0), reverse=True)

        return results

    @staticmethod
    def get_auto_complete_suggestions(query: str) -> dict:
        if not query or len(query.strip()) < 2:
            return {"suggestions": [], "correctedQuery": ""}

        q = query.lower().strip()
        suggestions = []
        best_correction = ""
        min_dist = 999

        # Check known dictionary
        for item in KNOWN_TECH_DICTIONARY:
            if item.lower().startswith(q):
                suggestions.append(item)
            dist = levenshtein_distance(q, item.lower())
            if dist < min_dist and dist <= 3:
                min_dist = dist
                best_correction = item

        # Check project titles
        projects = projects_repo.query(filters=[("visibility", "==", "public")], limit=50)
        for p in projects:
            title = p.get("title", "")
            if title.lower().startswith(q) and title not in suggestions:
                suggestions.append(title)

        return {
            "query": query,
            "suggestions": suggestions[:8],
            "correctedQuery": best_correction if (best_correction and best_correction.lower() != q) else query
        }

    @staticmethod
    def search_students(query: str = "", college: str = "", skill: str = ""):
        profiles = profiles_repo.query(filters=[("visibility", "==", "public")], limit=100)
        results = []

        q_lower = query.lower() if query else ""
        col_lower = college.lower() if college else ""
        skill_lower = skill.lower() if skill else ""

        for prof in profiles:
            match = True
            if q_lower:
                in_name = q_lower in prof.get("fullName", "").lower()
                in_spn = q_lower in prof.get("spn", "").lower()
                in_headline = q_lower in prof.get("headline", "").lower()
                if not (in_name or in_spn or in_headline):
                    match = False

            if col_lower and col_lower not in prof.get("college", "").lower():
                match = False

            if skill_lower:
                skills = [s.lower() for s in prof.get("skills", [])]
                if not any(skill_lower in s for s in skills):
                    match = False

            if match:
                results.append(prof)

        return results
