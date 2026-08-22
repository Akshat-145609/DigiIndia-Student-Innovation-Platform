from api.providers.firebase import FirestoreRepository

profiles_repo = FirestoreRepository("profiles")

class MatchmakingEngine:
    """
    Global Student Matchmaking Algorithm.
    Pairs student developers based on complementary skill gaps and collaboration interests.
    """

    @classmethod
    def match_students(cls, target_uid: str, limit: int = 10) -> list:
        target_profile = profiles_repo.get(target_uid)
        if not target_profile:
            profiles = profiles_repo.query(limit=limit)
            return profiles

        target_skills = set([s.lower() for s in target_profile.get("skills", [])])
        all_profiles = profiles_repo.query(filters=[("visibility", "==", "public")], limit=100)

        matches = []
        for prof in all_profiles:
            if prof.get("studentUID") == target_uid:
                continue

            prof_skills = set([s.lower() for s in prof.get("skills", [])])
            if not prof_skills:
                continue

            # Skill Complementarity: Skills prof has that target lacks
            complementary = prof_skills - target_skills
            common = prof_skills & target_skills

            # Score formula: 70% weight on complementary skills + 30% on common ground
            match_score = (len(complementary) * 20) + (len(common) * 5)
            match_score = min(98, max(50, match_score))

            matches.append({
                "studentUID": prof.get("studentUID"),
                "spn": prof.get("spn"),
                "fullName": prof.get("fullName"),
                "college": prof.get("college"),
                "trustScore": prof.get("trustScore", 40),
                "skills": prof.get("skills", []),
                "complementarySkills": [s.title() for s in complementary],
                "commonSkills": [s.title() for s in common],
                "matchScore": match_score,
                "recommendedRole": "Backend Lead" if "python" in prof_skills or "node.js" in prof_skills else "UI/UX Lead"
            })

        matches.sort(key=lambda x: x["matchScore"], reverse=True)
        return matches[:limit]
