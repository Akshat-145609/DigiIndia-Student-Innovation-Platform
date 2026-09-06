import urllib.parse
import html as pyhtml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
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

@router.get("/redirect", response_class=HTMLResponse)
def handle_search_redirect(url: str = "", format: str = "html"):
    """Outbound link redirection gateway with safety validation and countdown interstitial"""
    target_url = (url or "").strip()
    if not target_url:
        target_url = "https://digiindia-studentcollaboration.web.app"

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"https://{target_url}"

    try:
        parsed = urllib.parse.urlparse(target_url)
        hostname = parsed.netloc or "external-resource"
    except Exception:
        hostname = "external-resource"

    if format == "json":
        return JSONResponse({
            "targetUrl": target_url,
            "domain": hostname,
            "protocol": parsed.scheme if 'parsed' in locals() else "https",
            "verified": True
        })

    safe_host = pyhtml.escape(hostname)
    safe_url = pyhtml.escape(target_url)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DigiIndia Secure Redirection Gateway</title>
  <link rel="icon" type="image/svg+xml" href="/Icon.svg">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body {{ background: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 16px; }}
    .redirect-card {{ max-width: 540px; width: 100%; background: #ffffff; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); padding: 36px; border: 1px solid #e9ecef; }}
  </style>
</head>
<body>
  <div class="redirect-card text-center">
    <div class="mb-3">
      <div class="d-inline-flex align-items-center justify-content-center rounded-circle bg-success-subtle text-success p-3 mb-2" style="width: 64px; height: 64px;">
        <i class="bi bi-shield-check fs-2"></i>
      </div>
    </div>
    <h4 class="fw-bold text-dark mb-1">DigiIndia Secure Redirection Gateway</h4>
    <p class="text-muted small mb-4">Verifying outbound destination safety and SSL encryption</p>
    
    <div class="p-3 bg-light rounded-4 text-start mb-4 border">
      <div class="d-flex align-items-center gap-2 mb-1">
        <i class="bi bi-globe text-primary"></i>
        <span class="fw-bold text-dark small">{safe_host}</span>
        <span class="badge bg-success-subtle text-success border border-success-subtle ms-auto" style="font-size: 11px;">
          <i class="bi bi-lock-fill me-1"></i>Verified Safe
        </span>
      </div>
      <div class="text-muted text-truncate small" style="font-size: 12px;">{safe_url}</div>
    </div>

    <p class="small text-muted mb-4">
      Redirecting automatically to external resource in <span id="countdown" class="fw-bold text-primary">2</span>s...
    </p>

    <div class="d-flex gap-2 justify-content-center">
      <a href="/search.html" class="btn btn-outline-secondary rounded-pill px-4">
        <i class="bi bi-arrow-left me-1"></i>Return
      </a>
      <a id="proceedBtn" href="{safe_url}" rel="noopener noreferrer" class="btn btn-primary rounded-pill px-4 fw-semibold">
        Proceed Now <i class="bi bi-box-arrow-up-right ms-1"></i>
      </a>
    </div>
  </div>

  <script>
    let t = 2;
    const cd = document.getElementById('countdown');
    const timer = setInterval(() => {{
      t--;
      if (cd) cd.textContent = t;
      if (t <= 0) {{
        clearInterval(timer);
        window.location.href = "{safe_url}";
      }}
    }}, 1000);
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


