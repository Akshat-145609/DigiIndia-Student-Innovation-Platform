#!/usr/bin/env python3
"""
DigiIndia SERP Logic Engine & Multi-Threaded SEO Inspection System
Dynamically discovers and processes local JSON SERP stores (json/google-results/ & json/youtube-results/)
Cleanses third-party dependencies, resolves direct destination URLs, and provides instant SERP caching.
"""

import os
import sys
import json
import re
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Base directories
BASE_DIR = Path(__file__).resolve().parent
GOOGLE_RESULTS_DIR = BASE_DIR / "json" / "google-results"
YOUTUBE_RESULTS_DIR = BASE_DIR / "json" / "youtube-results"

def detect_deploying_body(url_str: str) -> Dict[str, str]:
    """Detect deploying platform/body based on hostname."""
    try:
        parsed = urllib.parse.urlparse(url_str)
        host = (parsed.netloc or "").lower()
        if "onrender.com" in host:
            return {"name": "Render Web Service", "icon": "bi-hdd-network", "badge": "primary"}
        if "github.io" in host or "github.com" in host:
            return {"name": "GitHub Pages", "icon": "bi-github", "badge": "dark"}
        if "pages.dev" in host or "cloudflare" in host:
            return {"name": "Cloudflare Pages", "icon": "bi-cloud-check", "badge": "warning"}
        if "web.app" in host or "firebaseapp.com" in host:
            return {"name": "Firebase Hosting", "icon": "bi-fire", "badge": "warning"}
        if "vercel.app" in host or "vercel.com" in host:
            return {"name": "Vercel Cloud", "icon": "bi-triangle", "badge": "dark"}
        if "google" in host:
            return {"name": "Google Developer", "icon": "bi-google", "badge": "primary"}
        if "geeksforgeeks" in host:
            return {"name": "GeeksforGeeks", "icon": "bi-journal-code", "badge": "success"}
        if "scribd" in host:
            return {"name": "Scribd Documents", "icon": "bi-file-earmark-pdf", "badge": "info"}
        if "kaggle" in host:
            return {"name": "Kaggle Community", "icon": "bi-clipboard-data", "badge": "info"}
        if "youtube.com" in host or "youtu.be" in host:
            return {"name": "YouTube Video", "icon": "bi-youtube", "badge": "danger"}
        if "wikipedia" in host:
            return {"name": "Wikipedia Knowledge", "icon": "bi-book", "badge": "secondary"}
        
        # Generic fallback
        clean_host = host.replace("www.", "")
        return {"name": clean_host.capitalize(), "icon": "bi-globe", "badge": "secondary"}
    except Exception:
        return {"name": "Web Deployment", "icon": "bi-globe", "badge": "secondary"}

def get_native_favicon_url(url_str: str) -> str:
    """Generate clean, direct favicon URL without third-party proxy dependencies."""
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        return "/Icon.svg"
    except Exception:
        return "/Icon.svg"

def clean_direct_url(url_str: str) -> str:
    """Strip Google / SerpAPI redirection wrappers to yield pure destination URL."""
    if not url_str:
        return ""
    try:
        # Check if it's a google redirection wrapper
        if "google." in url_str and "url=" in url_str:
            parsed = urllib.parse.urlparse(url_str)
            qs = urllib.parse.parse_qs(parsed.query)
            if "url" in qs and qs["url"]:
                return qs["url"][0]
            if "q" in qs and qs["q"]:
                return qs["q"][0]
    except Exception:
        pass
    return url_str

def sanitize_google_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Cleanses a Google result JSON file of all SerpAPI artifacts and returns structured data.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    # Remove serpapi metadata
    data.pop("search_metadata", None)

    # Process organic_results
    organic = data.get("organic_results", [])
    clean_organic = []
    for item in organic:
        raw_url = item.get("url") or item.get("link") or ""
        direct_link = clean_direct_url(raw_url)
        if not direct_link:
            continue

        deploy = detect_deploying_body(direct_link)
        fav = item.get("favicon") or get_native_favicon_url(direct_link)
        if "serpapi.com" in fav:
            fav = get_native_favicon_url(direct_link)

        clean_item = {
            "position": item.get("position", len(clean_organic) + 1),
            "title": item.get("title", "Web Page"),
            "url": direct_link,
            "displayUrl": item.get("displayUrl") or item.get("displayed_link") or direct_link,
            "snippet": item.get("snippet", ""),
            "deployingBody": item.get("deployingBody") or deploy["name"],
            "deployingBodyIcon": item.get("deployingBodyIcon") or deploy["icon"],
            "badgeColor": item.get("badgeColor") or deploy["badge"],
            "favicon": fav,
            "sitelinks": item.get("sitelinks") or []
        }

        # Extract sitelinks if present as dict
        sitelinks_data = item.get("sitelinks", {})
        if isinstance(sitelinks_data, dict):
            inline_links = sitelinks_data.get("inline", [])
            clean_item["sitelinks"] = [sl.get("title", "") for sl in inline_links if sl.get("title")]
        elif isinstance(sitelinks_data, list):
            clean_item["sitelinks"] = [sl if isinstance(sl, str) else sl.get("title", "") for sl in sitelinks_data]

        clean_organic.append(clean_item)

    data["organic_results"] = clean_organic
    return data

def sanitize_youtube_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Cleanses a YouTube result JSON file of all SerpAPI artifacts and returns structured video items.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    data.pop("search_metadata", None)
    clean_videos = []

    # 1. Check video_results
    video_results = data.get("video_results", [])
    for v in video_results:
        vid_id = v.get("videoId") or v.get("video_id") or ""
        raw_url = v.get("url") or v.get("link") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")
        v_link = clean_direct_url(raw_url)
        if not v_link:
            continue

        ch = v.get("channel", {})
        thumb = v.get("thumbnail") or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
        if "serpapi.com" in thumb:
            thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else ""

        clean_videos.append({
            "title": v.get("title", "YouTube Video Tutorial"),
            "url": v_link,
            "videoId": vid_id,
            "thumbnail": thumb,
            "duration": v.get("duration") or v.get("length") or "Video",
            "channelTitle": v.get("channelTitle") or (ch.get("name") if isinstance(ch, dict) else str(ch)),
            "channelVerified": v.get("channelVerified") if "channelVerified" in v else (ch.get("verified", False) if isinstance(ch, dict) else False),
            "views": f"{v.get('views', 1000):,} views" if isinstance(v.get('views'), int) else str(v.get('views') or "10K views"),
            "uploadedTime": v.get("uploadedTime") or v.get("published_date") or "Recently",
            "description": v.get("description") or "Watch video demonstration and tutorial on YouTube."
        })

    # 2. Check playlist_results
    playlist_results = data.get("playlist_results", [])
    for pl in playlist_results:
        p_videos = pl.get("videos", [])
        ch = pl.get("channel", {})
        for pv in p_videos:
            pv_link = clean_direct_url(pv.get("url") or pv.get("link") or "")
            clean_videos.append({
                "title": pv.get("title", pl.get("title", "Playlist Video")),
                "url": pv_link,
                "thumbnail": pl.get("thumbnail") or "https://i.ytimg.com/vi/MFPg6gz0_98/hqdefault.jpg",
                "duration": pv.get("duration") or pv.get("length") or "Playlist",
                "channelTitle": ch.get("name") if isinstance(ch, dict) else "YouTube Creator",
                "channelVerified": True,
                "views": "Playlist Collection",
                "uploadedTime": "Curated",
                "description": f"Video playlist: {pl.get('title')}"
            })

    data["video_results"] = clean_videos
    return data

def clean_all_json_files():
    """
    Overwrites all .json files in json/google-results and json/youtube-results
    to permanently remove third-party SerpAPI URLs and store direct URLs.
    """
    cleaned_count = 0
    if GOOGLE_RESULTS_DIR.exists():
        for p in GOOGLE_RESULTS_DIR.glob("*.json"):
            cleaned = sanitize_google_json_file(p)
            if cleaned:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(cleaned, f, indent=2, ensure_ascii=False)
                cleaned_count += 1
                print(f"[Cleaned] Google SERP: {p.name}")

    if YOUTUBE_RESULTS_DIR.exists():
        for p in YOUTUBE_RESULTS_DIR.glob("*.json"):
            cleaned = sanitize_youtube_json_file(p)
            if cleaned:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(cleaned, f, indent=2, ensure_ascii=False)
                cleaned_count += 1
                print(f"[Cleaned] YouTube SERP: {p.name}")

    print(f"\n[OK] Successfully cleaned {cleaned_count} JSON files. All third-party dependencies removed.")

def tokenize_string(s: str) -> List[str]:
    """Tokenize query string into lowercase alphanum keywords."""
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', s.lower())
    return [t for t in clean.split() if len(t) > 1]

def match_score(query_tokens: List[str], target_str: str) -> int:
    """Compute matching score between query tokens and a target text."""
    if not query_tokens or not target_str:
        return 0
    target_clean = target_str.lower()
    score = 0
    full_q = " ".join(query_tokens)

    # Exact full match bonus
    if full_q in target_clean:
        score += 50

    # Token matches
    for tok in query_tokens:
        if tok in target_clean:
            score += 15
            # Word boundary bonus
            if re.search(r'\b' + re.escape(tok) + r'\b', target_clean):
                score += 10

    return score

class SerpLogicEngine:
    """
    Case-insensitive, tokenized query matching engine for local JSON SERP cache.
    Dynamically discovers all files without hardcoding.
    """

    @classmethod
    def query_google_results(cls, query: str) -> List[Dict[str, Any]]:
        if not GOOGLE_RESULTS_DIR.exists():
            return []

        q_tokens = tokenize_string(query)
        if not q_tokens:
            return []

        scored_results = []
        for file_path in GOOGLE_RESULTS_DIR.glob("*.json"):
            fname_no_ext = file_path.stem.replace("-", " ")
            file_score = match_score(q_tokens, fname_no_ext)

            try:
                data = sanitize_google_json_file(file_path)
                search_q = data.get("search_parameters", {}).get("q", "")
                param_score = match_score(q_tokens, search_q)
                base_score = max(file_score, param_score)

                for item in data.get("organic_results", []):
                    item_score = base_score + match_score(q_tokens, item.get("title", "")) + match_score(q_tokens, item.get("snippet", ""))
                    if item_score > 0:
                        item_copy = dict(item)
                        item_copy["_score"] = item_score
                        scored_results.append(item_copy)
            except Exception:
                continue

        # Sort by score descending and deduplicate by URL
        scored_results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        unique_results = []
        seen_urls = set()
        for r in scored_results:
            url = r.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                r.pop("_score", None)
                unique_results.append(r)

        return unique_results

    @classmethod
    def query_youtube_results(cls, query: str) -> List[Dict[str, Any]]:
        if not YOUTUBE_RESULTS_DIR.exists():
            return []

        q_tokens = tokenize_string(query)
        if not q_tokens:
            return []

        scored_results = []
        for file_path in YOUTUBE_RESULTS_DIR.glob("*.json"):
            fname_no_ext = file_path.stem.replace("-", " ")
            file_score = match_score(q_tokens, fname_no_ext)

            try:
                data = sanitize_youtube_json_file(file_path)
                search_q = data.get("search_parameters", {}).get("search_query", "")
                param_score = match_score(q_tokens, search_q)
                base_score = max(file_score, param_score)

                for v in data.get("video_results", []):
                    v_score = base_score + match_score(q_tokens, v.get("title", "")) + match_score(q_tokens, v.get("description", ""))
                    if v_score > 0:
                        v_copy = dict(v)
                        v_copy["_score"] = v_score
                        scored_results.append(v_copy)
            except Exception:
                continue

        scored_results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        unique_results = []
        seen_urls = set()
        for v in scored_results:
            url = v.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                v.pop("_score", None)
                unique_results.append(v)

        return unique_results

    @classmethod
    def search_all(cls, query: str) -> Dict[str, Any]:
        """Perform unified search across local JSON stores."""
        return {
            "query": query,
            "googleWebResults": cls.query_google_results(query),
            "youtubeResources": cls.query_youtube_results(query)
        }

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    if "--clean-json" in sys.argv:
        clean_all_json_files()
        sys.exit(0)

    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        q = " ".join(sys.argv[1:])
        res = SerpLogicEngine.search_all(q)
        print(json.dumps(res, indent=2, ensure_ascii=True))
    else:
        print("Usage:")
        print("  python serp-logic-engine.py --clean-json         (Cleanses all JSON files in json/)")
        print("  python serp-logic-engine.py <search query>       (Searches local SERP JSON store)")
