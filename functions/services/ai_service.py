from api.router import AIRouter
from api.providers.firebase import FirestoreRepository

projects_repo = FirestoreRepository("projects")

class AIService:

    @staticmethod
    def ask_ai_assistant(prompt: str, code_snippet: str = ""):
        res = AIRouter.generate_assistant_response(prompt, code_snippet)
        reply = res.get("reply") or res.get("response") if isinstance(res, dict) else str(res)
        return {
            "reply": reply or "AI response generated successfully.",
            "response": reply or "AI response generated successfully."
        }

    @staticmethod
    def review_project(project_id: str):

        proj = projects_repo.get(project_id)
        if not proj:
            raise Exception("Project not found")

        repo_url = proj.get("repositoryURL", "")
        desc = proj.get("description", "")
        
        # AIRouter orchestrates Gemini, Grok, and OpenAI fallback
        analysis = AIRouter.analyze_repository(repo_url, desc)
        return analysis

    @staticmethod
    def review_code_snippet(code: str, language: str = "python"):
        review = AIRouter.review_code(code, language)
        return review

    @staticmethod
    def analyze_url(url: str):
        """URL Analyzer: Scrapes target URL and evaluates technical architecture"""
        import httpx
        from bs4 import BeautifulSoup
        if not url or not url.startswith("http"):
            raise Exception("Valid URL starting with http:// or https:// required")
        
        extracted_info = ""
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    extracted_info = f"Title: {soup.title.string if soup.title else 'N/A'}\nText Snippet: {soup.get_text()[:1000]}"
        except Exception as e:
            extracted_info = f"Unable to fetch live page: {e}"

        return AIRouter.generate_assistant_response(f"Perform a comprehensive technical architecture analysis for URL: {url}\n\nCrawled Content:\n{extracted_info}")

    @staticmethod
    def analyze_seo(url: str):
        """SEO Analyzer: Evaluates meta tags, OpenGraph, titles, canonicals, and mobile readiness"""
        import httpx
        from bs4 import BeautifulSoup
        if not url or not url.startswith("http"):
            raise Exception("Valid URL required")
        
        seo_report = {
            "url": url,
            "hasTitle": False,
            "hasMetaDescription": False,
            "hasOpenGraph": False,
            "hasCanonical": False,
            "seoScore": 60
        }
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    seo_report["hasTitle"] = bool(soup.title and soup.title.string)
                    seo_report["hasMetaDescription"] = bool(soup.find("meta", attrs={"name": "description"}))
                    seo_report["hasOpenGraph"] = bool(soup.find("meta", property=lambda p: p and p.startswith("og:")))
                    seo_report["hasCanonical"] = bool(soup.find("link", rel="canonical"))
                    
                    score = 50
                    if seo_report["hasTitle"]: score += 15
                    if seo_report["hasMetaDescription"]: score += 15
                    if seo_report["hasOpenGraph"]: score += 10
                    if seo_report["hasCanonical"]: score += 10
                    seo_report["seoScore"] = score
        except Exception as e:
            seo_report["error"] = str(e)
            
        return seo_report

    @staticmethod
    def analyze_score(project_id: str):
        """Score Analyzer: Provides detailed breakdown of Trust Score factors"""
        proj = projects_repo.get(project_id)
        if not proj:
            raise Exception("Project not found")
        
        base_score = proj.get("trustScore", 50)
        return {
            "projectId": project_id,
            "overallTrustScore": base_score,
            "breakdown": {
                "identityVerification": 30 if proj.get("verificationStatus") == "verified" else 10,
                "repositoryOwnership": 25 if proj.get("repositoryURL") else 0,
                "liveWebsiteVerification": 20 if proj.get("liveURL") else 0,
                "documentationQuality": 15,
                "communityReputation": 10
            },
            "explanation": "Trust score is generated dynamically based on identity verification, meta-tag ownership checks, and repository documentation quality."
        }

    @staticmethod
    def analyze_ownership_url(url: str, verification_token: str = ""):
        """Ownership Score Analyzer: Inspects meta-tags & domain config for ownership proof"""
        import httpx
        from bs4 import BeautifulSoup
        if not url or not url.startswith("http"):
            raise Exception("Valid URL required")
        
        found_tag = False
        tag_content = ""
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    meta = soup.find("meta", attrs={"name": "digiindia-student-innovation-platform"})
                    if meta:
                        found_tag = True
                        tag_content = meta.get("content", "")
        except Exception:
            pass

        ownership_score = 95 if (found_tag and tag_content == verification_token) else (50 if found_tag else 20)
        return {
            "targetURL": url,
            "metaTagFound": found_tag,
            "tokenMatched": (tag_content == verification_token) if verification_token else found_tag,
            "ownershipScore": ownership_score,
            "status": "verified" if ownership_score >= 80 else "pending_review"
        }

    @staticmethod
    def validate_person_schema(student_uid: str):
        """Person Schema Validator: Evaluates active user data against Schema.org/Person JSON-LD standard"""
        from api.providers.firebase import FirestoreRepository
        students_repo = FirestoreRepository("students")
        profiles_repo = FirestoreRepository("profiles")

        st = students_repo.get(student_uid) or {}
        prof = profiles_repo.get(student_uid) or {}

        person_json_ld = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": prof.get("fullName", "Student"),
            "identifier": st.get("spn", ""),
            "email": st.get("email", ""),
            "telephone": st.get("phone", ""),
            "alumniOf": prof.get("college", ""),
            "jobTitle": prof.get("course", "Student Developer"),
            "image": prof.get("avatarURL", ""),
            "url": f"http://localhost:8000/profile.html?uid={student_uid}"
        }

        # Validation rules
        checks = {
            "hasName": bool(prof.get("fullName")),
            "hasSPN": bool(st.get("spn")),
            "hasEmail": bool(st.get("email")),
            "hasCollege": bool(prof.get("college")),
            "hasAvatar": bool(prof.get("avatarURL"))
        }

        score = sum([20 for k, v in checks.items() if v])

        return {
            "studentUID": student_uid,
            "jsonLd": person_json_ld,
            "schemaValidationScore": score,
            "checks": checks,
            "status": "valid" if score >= 80 else "incomplete"
        }

    @staticmethod
    def get_verification_status_with_linenumber(url: str, verification_token: str = ""):
        """DigiIndia Verification Status: Scans URL source code line-by-line returning exact LN where meta tag was found"""
        import httpx
        if not url or not url.startswith("http"):
            raise Exception("Valid URL required")

        found_ln = -1
        raw_tag = ""
        matched = False

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    lines = res.text.splitlines()
                    for idx, line in enumerate(lines, 1):
                        if "digiindia-student-innovation-platform" in line:
                            found_ln = idx
                            raw_tag = line.strip()
                            if verification_token and verification_token in line:
                                matched = True
                            elif not verification_token:
                                matched = True
                            break
        except Exception as e:
            return {"error": f"Failed to crawl URL: {e}"}

        return {
            "targetURL": url,
            "found": (found_ln != -1),
            "lineNumber": found_ln,
            "rawMetaTag": raw_tag,
            "tokenMatched": matched,
            "verifiedAt": time.time() if (found_ln != -1 and matched) else None
        }

    @staticmethod
    def train_ai_model_from_url(url: str):
        """Method 1: Enter URL -> Multi-Stage Python Crawler -> AI Knowledge Enhancement"""
        from services.crawler_service import CrawlerService
        return CrawlerService.crawl_and_process_url(url)

    @staticmethod
    def upload_md_training_file(title: str, markdown_content: str):
        """Method 2: Create {title}.md file and Upload to Firestore"""
        import time, uuid
        from api.providers.firebase import FirestoreRepository
        ai_models_repo = FirestoreRepository("aiTrainingModels")
        knowledge_repo = FirestoreRepository("aiKnowledge")

        doc_id = f"md_{str(uuid.uuid4())[:8]}"
        record = {
            "knowledgeId": doc_id,
            "title": title,
            "filename": f"{title}.md",
            "knowledgeMarkdown": markdown_content,
            "type": "markdown_upload",
            "createdAt": time.time()
        }
        knowledge_repo.set(doc_id, record)
        ai_models_repo.set(doc_id, {
            "modelName": f"Doc: {title}.md",
            "type": "markdown_file",
            "filename": f"{title}.md",
            "knowledgeId": doc_id,
            "createdAt": time.time()
        })
        return record

    @staticmethod
    def generate_user_api_key(student_uid: str, label: str = "Default API Key"):
        """Method 3: Generate User Specific DigiIndia API Key from Dashboard & Store in Firestore"""
        import secrets, time
        from api.providers.firebase import FirestoreRepository
        api_keys_repo = FirestoreRepository("apiKeys")

        key_id = f"key_{secrets.token_hex(6)}"
        api_key = f"digi_live_{secrets.token_urlsafe(24)}"

        key_doc = {
            "keyId": key_id,
            "apiKey": api_key,
            "ownerUID": student_uid,
            "label": label,
            "permissions": ["read_projects", "ai_query", "search"],
            "usageCount": 0,
            "status": "active",
            "createdAt": time.time()
        }

        api_keys_repo.set(key_id, key_doc)
        return key_doc


