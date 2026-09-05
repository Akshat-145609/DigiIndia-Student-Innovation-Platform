import os
import sys
from pathlib import Path
from urllib.parse import quote
import httpx

# Ensure parent directory is in sys.path to import serp_logic_engine
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from serp_logic_engine import SerpLogicEngine
except ImportError:
    # Try alternate import path
    import importlib.util
    spec = importlib.util.spec_from_file_location("serp_logic_engine", str(ROOT_DIR / "serp-logic-engine.py"))
    if spec and spec.loader:
        serp_logic_engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(serp_logic_engine)
        SerpLogicEngine = serp_logic_engine.SerpLogicEngine
    else:
        SerpLogicEngine = None

from services.multi_threaded_crawler import MultiThreadedLiveCrawler, USER_AGENT

class GlobalWebService:
    """
    Unified search service combining local JSON cache, live multi-threaded web crawl (Google CSE & DDG),
    live YouTube inspection, and GitHub public repositories.
    """

    @classmethod
    def fetch_global_web_results(cls, query: str) -> dict:
        if not query or len(query.strip()) < 2:
            query = "student innovation projects"

        clean_q = query.strip()
        encoded_q = quote(clean_q)
        headers = {"User-Agent": USER_AGENT}

        # 1. Check local JSON cache via SerpLogicEngine (Instant)
        cached_google = []
        cached_yt = []
        if SerpLogicEngine:
            try:
                cached_res = SerpLogicEngine.search_all(clean_q)
                cached_google = cached_res.get("googleWebResults", [])
                cached_yt = cached_res.get("youtubeResources", [])
            except Exception:
                pass

        # 2. Fetch Live Web Results via MultiThreadedLiveCrawler
        live_google = []
        try:
            live_google = MultiThreadedLiveCrawler.crawl_google_web(clean_q, limit=6)
        except Exception:
            pass

        # Merge and deduplicate Google Web Results
        merged_google = []
        seen_google_urls = set()
        for item in (cached_google + live_google):
            u = item.get("url")
            if u and u not in seen_google_urls:
                seen_google_urls.add(u)
                merged_google.append(item)

        # 3. Fetch Live YouTube Videos via MultiThreadedLiveCrawler
        live_yt = []
        try:
            live_yt = MultiThreadedLiveCrawler.crawl_youtube_videos(clean_q, limit=6)
        except Exception:
            pass

        # Merge and deduplicate YouTube Videos
        merged_yt = []
        seen_yt_urls = set()
        for item in (cached_yt + live_yt):
            u = item.get("url")
            if u and u not in seen_yt_urls:
                seen_yt_urls.add(u)
                merged_yt.append(item)

        # 4. Fetch GitHub Repositories
        github_results = []
        try:
            gh_url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page=6"
            with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                res = client.get(gh_url, headers=headers)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    for item in items:
                        github_results.append({
                            "title": item["name"],
                            "full_name": item["full_name"],
                            "description": item.get("description") or "Open source repository on GitHub.",
                            "url": item["html_url"],
                            "stars": item.get("stargazers_count", 0),
                            "language": item.get("language") or "Code",
                            "owner": item["owner"]["login"],
                            "avatar": item["owner"]["avatar_url"]
                        })
        except Exception:
            pass

        return {
            "query": clean_q,
            "googleWebResults": merged_google[:10],
            "youtubeResources": merged_yt[:8],
            "githubRepositories": github_results
        }
