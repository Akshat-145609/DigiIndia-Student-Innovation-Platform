from fastapi import APIRouter
from services.search_service import SearchService
from services.vector_search_service import VectorSearchEngine
from services.digibot_service import DigiBotCrawler
from services.localization_service import LocalizationEngine

router = APIRouter(prefix="/search", tags=["Global Search Engine"])

@router.get("/projects")
def search_projects(
    q: str = "",
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
    return SearchService.search_projects(
        query=q,
        technology=technology,
        institution=institution,
        verified_only=verified_only,
        language=language,
        license_type=license_type,
        min_stars=min_stars,
        min_trust_score=min_trust_score,
        country=country,
        sort_by=sort_by
    )

@router.get("/semantic")
def semantic_search(q: str = "", limit: int = 20):
    return VectorSearchEngine.semantic_search(query=q, limit=limit)

@router.get("/autocomplete")
def autocomplete(q: str = ""):
    return SearchService.get_auto_complete_suggestions(query=q)

@router.post("/digibot/crawl")
def run_digibot_crawl(query: str = "student project", source: str = "all", max_results: int = 10):
    return DigiBotCrawler.run_crawl_cycle(query=query, source=source, max_results=max_results)

@router.get("/digibot/status")
def get_digibot_status():
    return DigiBotCrawler.get_bot_status()

@router.get("/translate")
def translate_query(text: str = "", target_lang: str = "en"):
    return {
        "originalText": text,
        "targetLang": target_lang,
        "translatedText": LocalizationEngine.translate_summary(text, target_lang)
    }

from services.global_web_service import GlobalWebService

@router.get("/global-live")
def get_global_live_results(q: str = ""):
    return GlobalWebService.fetch_global_web_results(q)

@router.get("/students")
def search_students(q: str = "", college: str = "", skill: str = ""):
    return SearchService.search_students(q, college, skill)

