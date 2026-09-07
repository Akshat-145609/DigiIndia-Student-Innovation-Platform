import urllib.parse
import html as pyhtml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from services.search_service import SearchService
from services.vector_search_service import VectorSearchEngine
from services.digibot_service import DigiBotCrawler
from services.localization_service import LocalizationEngine
from services.security_scanner_service import SecurityScannerService

router = APIRouter(prefix="/search", tags=["Global Search Engine"])

@router.get("/analyze-url")
@router.post("/analyze-url")
def analyze_destination_url(url: str = ""):
    """Live destination URL security analysis with DOM inspection and AI technical brief"""
    if not url:
        return JSONResponse(status_code=400, content={"detail": "Missing destination URL (?url=...)"})
    return SecurityScannerService.deep_analyze(url)

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
    """Outbound link redirection gateway with safety validation, quick regex checking, and AI security diagnostics"""
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

    # Fast-Path Security Evaluation (< 2ms)
    scan = SecurityScannerService.quick_check(target_url)
    is_suspicious = scan.get("is_suspicious", False)
    risk_level = scan.get("risk_level", "safe")
    reasons = scan.get("reasons", [])

    if format == "json":
        return JSONResponse({
            "targetUrl": target_url,
            "domain": hostname,
            "protocol": parsed.scheme if 'parsed' in locals() else "https",
            "isSuspicious": is_suspicious,
            "riskLevel": risk_level,
            "riskScore": scan.get("risk_score", 0),
            "reasons": reasons,
            "verified": not is_suspicious
        })

    safe_host = pyhtml.escape(hostname)
    safe_url = pyhtml.escape(target_url)
    reasons_badges_html = "".join([f'<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2 rounded-pill small mb-1 text-wrap text-start"><i class="bi bi-shield-x me-1"></i>{pyhtml.escape(r)}</span>' for r in reasons])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DigiIndia Secure Redirection Gateway</title>
  <link rel="icon" type="image/svg+xml" href="/Icon.svg">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    body {{ background: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 16px; }}
    .redirect-card {{ max-width: 540px; width: 100%; background: #ffffff; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); padding: 36px; border: 1px solid #e9ecef; }}
    .sandbox-doc-view {{ color: #1e293b; font-size: 14.5px; line-height: 1.75; }}
    .sandbox-doc-view h1, .sandbox-doc-view h2, .sandbox-doc-view h3 {{ color: #0f172a; font-weight: 700; margin-top: 18px; margin-bottom: 10px; }}
    .sandbox-doc-view table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13.5px; }}
    .sandbox-doc-view table th, .sandbox-doc-view table td {{ border: 1px solid #cbd5e1; padding: 8px 12px; }}
    .sandbox-doc-view table th {{ background: #f1f5f9; color: #0f172a; }}
    .sandbox-doc-view pre {{ background: #1e1e2e; color: #cdd6f4; padding: 14px; border-radius: 8px; overflow-x: auto; }}
  </style>
</head>
<body>

  <!-- MAIN GATEWAY CARD -->
  <div class="redirect-card text-center">
    <div class="mb-3">
      <div class="d-inline-flex align-items-center justify-content-center rounded-circle {'bg-danger-subtle text-danger' if is_suspicious else 'bg-success-subtle text-success'} p-3 mb-2" style="width: 64px; height: 64px;">
        <i class="bi {'bi-shield-exclamation' if is_suspicious else 'bi-shield-check'} fs-2"></i>
      </div>
    </div>
    <h4 class="fw-bold text-dark mb-1">DigiIndia Secure Redirection Gateway</h4>
    <p class="text-muted small mb-4">Verifying outbound destination safety and SSL encryption</p>
    
    <div class="p-3 bg-light rounded-4 text-start mb-4 border">
      <div class="d-flex align-items-center gap-2 mb-1">
        <i class="bi bi-globe text-primary"></i>
        <span class="fw-bold text-dark small">{safe_host}</span>
        <span class="badge {'bg-danger-subtle text-danger border border-danger-subtle' if is_suspicious else 'bg-success-subtle text-success border border-success-subtle'} ms-auto" style="font-size: 11px;">
          <i class="bi {'bi-exclamation-triangle-fill' if is_suspicious else 'bi-lock-fill'} me-1"></i>{'Suspicious Link Flagged' if is_suspicious else 'Verified Safe'}
        </span>
      </div>
      <div class="text-muted text-truncate small" style="font-size: 12px;">{safe_url}</div>
    </div>

    {'<div class="alert alert-danger text-start p-3 rounded-4 mb-4 small"><div class="d-flex align-items-center gap-2 mb-2 text-danger fw-bold"><i class="bi bi-exclamation-octagon-fill"></i>Threat Warning: Automatic redirection blocked</div><div class="d-flex flex-column gap-1">' + reasons_badges_html + '</div></div>' if is_suspicious else f'''
    <p class="small text-muted mb-4">
      Redirecting automatically to external resource in <span id="countdown" class="fw-bold text-primary">2</span>s...
    </p>
    '''}

    <div class="d-flex gap-2 justify-content-center">
      <a href="/search.html" class="btn btn-outline-secondary rounded-pill px-4">
        <i class="bi bi-arrow-left me-1"></i>Return
      </a>
      <a id="proceedBtn" href="{safe_url}" rel="noopener noreferrer" class="btn {'btn-danger' if is_suspicious else 'btn-primary'} rounded-pill px-4 fw-semibold">
        {'Proceed Anyway (Unsafe)' if is_suspicious else 'Proceed Now'} <i class="bi bi-box-arrow-up-right ms-1"></i>
      </a>
    </div>
  </div>

  <!-- 1. ALERT CONFIRMATION MODAL (SHOWN ONLY AND ONLY WHEN DESTINATION IS SUSPICIOUS) -->
  <div class="modal fade" id="suspiciousAlertModal" tabindex="-1" aria-labelledby="suspiciousAlertModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content rounded-4 border-0 shadow-lg position-relative overflow-hidden">
        <!-- Top-Left Cross Icon to cancel and return -->
        <button type="button" class="btn btn-sm btn-light border rounded-circle position-absolute d-flex align-items-center justify-content-center shadow-sm" 
                style="top: 14px; left: 14px; width: 34px; height: 34px; z-index: 1060;" 
                onclick="cancelAndReturn()" aria-label="Close" title="Cancel & Return to Safety">
          <i class="bi bi-x-lg text-dark"></i>
        </button>

        <div class="modal-header border-bottom-0 pb-0 pt-4 px-4 ps-5">
          <div class="ms-3">
            <span class="badge bg-danger text-white rounded-pill px-3 py-1 mb-1">
              <i class="bi bi-shield-fill-exclamation me-1"></i>Security Warning
            </span>
            <h5 class="modal-title fw-bold text-danger mb-0" id="suspiciousAlertModalLabel">Suspicious Destination Detected</h5>
          </div>
        </div>

        <div class="modal-body px-4 py-3">
          <p class="text-muted small mb-3">
            DigiIndia AI Security Scanner inspected this outbound link and flagged it as potentially hazardous. Automatic redirection has been blocked for your safety.
          </p>

          <div class="p-3 bg-light rounded-3 border mb-3">
            <div class="small fw-semibold text-dark mb-1 text-truncate"><i class="bi bi-link-45deg me-1 text-primary"></i>{safe_url}</div>
            <div class="small text-muted mb-2">Host: <strong>{safe_host}</strong></div>
            <div class="d-flex flex-column gap-1">
              {reasons_badges_html}
            </div>
          </div>

          <p class="small text-secondary mb-0">
            Click the <strong class="text-info"><i class="bi bi-info-circle-fill me-1"></i>info icon</strong> below to inspect the complete <strong>AI System Scanner Live URL Test Report</strong> and DOM source code diagnosis.
          </p>
        </div>

        <div class="modal-footer border-top-0 pt-0 pb-4 px-4 d-flex justify-content-between align-items-center">
          <!-- Info Icon Button as requested -->
          <button type="button" class="btn btn-outline-info rounded-circle d-flex align-items-center justify-content-center shadow-sm" 
                  style="width: 40px; height: 40px;" 
                  onclick="openAiSecurityReportModal()" 
                  title="View AI Live Scanner Report & Technical Brief">
            <i class="bi bi-info-lg fs-5"></i>
          </button>

          <div class="d-flex gap-2">
            <button type="button" class="btn btn-outline-secondary rounded-pill px-3" onclick="cancelAndReturn()">
              <i class="bi bi-arrow-left me-1"></i>Return to Safety
            </button>
            <a href="{safe_url}" rel="noopener noreferrer" class="btn btn-danger rounded-pill px-3 fw-semibold">
              Proceed Anyway <i class="bi bi-exclamation-triangle-fill ms-1"></i>
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 2. AI SYSTEM SCANNER LIVE URL TEST REPORT / DIAGNOSIS MODAL -->
  <div class="modal fade" id="aiSecurityReportModal" tabindex="-1" aria-labelledby="aiSecurityReportModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content rounded-4 border-0 shadow-lg position-relative overflow-hidden">
        <!-- Top-Left Cross Icon to close report modal -->
        <button type="button" class="btn btn-sm btn-light border rounded-circle position-absolute d-flex align-items-center justify-content-center shadow-sm" 
                style="top: 14px; left: 14px; width: 34px; height: 34px; z-index: 1060;" 
                onclick="closeAiSecurityModal()" aria-label="Close" title="Close Report">
          <i class="bi bi-x-lg text-dark"></i>
        </button>

        <div class="modal-header border-bottom bg-light pt-3 pb-3 px-4 ps-5">
          <div class="ms-3">
            <div class="d-flex align-items-center gap-2 mb-1">
              <span class="badge bg-primary text-white"><i class="bi bi-robot me-1"></i>DigiIndia AI Scanner</span>
              <span class="badge bg-white text-secondary border"><i class="bi bi-cpu me-1"></i>Live Python Engine & DOM Audit</span>
            </div>
            <h5 class="modal-title fw-bold text-dark mb-0" id="aiSecurityReportModalLabel">AI System Scanner – Live URL Diagnosis</h5>
          </div>
        </div>

        <div class="modal-body p-4" id="aiSecurityReportModalBody">
          <div class="text-center py-5" id="aiReportLoadingState">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <h6 class="fw-bold text-dark">Performing Live Destination URL Diagnosis...</h6>
            <p class="small text-muted mb-0">Auditing server SSL, fetching DOM source code, running heuristics, and synthesizing AI technical brief.</p>
          </div>
          <div id="aiReportContentState" class="d-none sandbox-doc-view">
            <!-- Rendered README.md markdown from AI System Scanner injected here -->
          </div>
        </div>

        <div class="modal-footer border-top bg-light px-4 py-3 d-flex justify-content-between align-items-center">
          <button type="button" class="btn btn-secondary rounded-pill px-3 btn-sm" onclick="closeAiSecurityModal()">
            <i class="bi bi-x-circle me-1"></i>Close Report
          </button>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-outline-secondary rounded-pill px-3 btn-sm" onclick="cancelAndReturn()">
              Return to Safety
            </button>
            <a href="{safe_url}" rel="noopener noreferrer" class="btn btn-danger rounded-pill px-3 btn-sm fw-semibold">
              Proceed to Destination (Unsafe) <i class="bi bi-box-arrow-up-right ms-1"></i>
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const isSuspicious = {'true' if is_suspicious else 'false'};
    const targetUrl = "{safe_url}";
    let alertModalInstance = null;
    let aiReportModalInstance = null;

    function cancelAndReturn() {{
      if (window.history.length > 1) {{
        window.history.back();
      }} else {{
        window.location.href = "/search.html";
      }}
    }}

    function openAiSecurityReportModal() {{
      // Cancel / hide the Alert Confirmation Modal
      if (alertModalInstance) {{
        alertModalInstance.hide();
      }}
      // Open the AI System Scanner Report Modal
      const reportEl = document.getElementById('aiSecurityReportModal');
      if (reportEl && window.bootstrap) {{
        aiReportModalInstance = new bootstrap.Modal(reportEl);
        aiReportModalInstance.show();
        fetchLiveSecurityReport();
      }}
    }}

    function closeAiSecurityModal() {{
      if (aiReportModalInstance) {{
        aiReportModalInstance.hide();
      }}
    }}

    async function fetchLiveSecurityReport() {{
      const loadingState = document.getElementById('aiReportLoadingState');
      const contentState = document.getElementById('aiReportContentState');
      try {{
        const res = await fetch(`/api/v1/search/analyze-url?url=${{encodeURIComponent(targetUrl)}}`);
        const data = await res.json();
        if (loadingState) loadingState.classList.add('d-none');
        if (contentState) {{
          contentState.classList.remove('d-none');
          const markdownText = data.aiReportMarkdown || "### No Report Generated";
          contentState.innerHTML = (typeof marked !== "undefined") ? marked.parse(markdownText) : markdownText;
        }}
      }} catch (err) {{
        if (loadingState) loadingState.classList.add('d-none');
        if (contentState) {{
          contentState.classList.remove('d-none');
          contentState.innerHTML = `<div class="alert alert-warning">Unable to complete live audit: ${{err.message}}</div>`;
        }}
      }}
    }}

    document.addEventListener("DOMContentLoaded", () => {{
      if (isSuspicious) {{
        // ONLY AND ONLY WHEN suspicious: Halt redirect and show Alert Confirmation Modal
        const alertEl = document.getElementById('suspiciousAlertModal');
        if (alertEl && window.bootstrap) {{
          alertModalInstance = new bootstrap.Modal(alertEl);
          alertModalInstance.show();
        }}
      }} else {{
        // Normal Safe Destination: Countdown and redirect smoothly
        let t = 2;
        const cd = document.getElementById('countdown');
        const timer = setInterval(() => {{
          t--;
          if (cd) cd.textContent = t;
          if (t <= 0) {{
            clearInterval(timer);
            window.location.href = targetUrl;
          }}
        }}, 1000);
      }}
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


