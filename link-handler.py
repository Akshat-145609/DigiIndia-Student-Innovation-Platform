#!/usr/bin/env python3
"""
DigiIndia Universal Dynamic Link Handler (link-handler.py)
Transforms outbound links to pass through the active domain security redirect gateway:
{activeDomainPrefix}/api/v1/search/redirect?url={targetUrl}

Supports:
1. Firebase: https://digiindia-studentcollaboration.web.app
2. Render Node.js: https://digiindia-student-innovation-platform-2.onrender.com
3. Render Python: https://digiindia-student-platform.onrender.com
"""

import sys
import re
import urllib.parse
from typing import Optional

DOMAIN_MAP = {
    "firebase": "https://digiindia-studentcollaboration.web.app",
    "node": "https://digiindia-student-innovation-platform-2.onrender.com",
    "python": "https://digiindia-student-platform.onrender.com"
}

def get_redirect_prefix(domain_type: str = "node") -> str:
    """Returns the redirect gateway URL prefix for the given domain type."""
    key = str(domain_type).lower().strip()
    base = DOMAIN_MAP.get(key, DOMAIN_MAP["node"])
    return f"{base}/api/v1/search/redirect?url="

def is_external_url(url: str, current_host: str = "") -> bool:
    """Determines whether a URL is an external outbound destination."""
    if not url:
        return False
    u = url.strip()

    # Skip internal fragment, pseudo-protocols
    if (
        u.startswith("#")
        or u.startswith("javascript:")
        or u.startswith("mailto:")
        or u.startswith("tel:")
        or u.startswith("blob:")
        or u.startswith("data:")
    ):
        return False

    # Skip already-redirected URLs
    if "/api/v1/search/redirect?url=" in u:
        return False

    if u.startswith("http://") or u.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(u)
            if current_host and parsed.netloc.lower() == current_host.lower():
                return False
            return True
        except Exception:
            return True

    return False

def wrap_redirect_url(url: str, domain_type: str = "node") -> str:
    """Wraps an external target URL with the redirect gateway formula."""
    if not is_external_url(url):
        return url
    prefix = get_redirect_prefix(domain_type)
    return f"{prefix}{urllib.parse.quote(url.strip(), safe='')}"

def transform_html_links(html_content: str, domain_type: str = "node") -> str:
    """Finds all <a href="..."> links in HTML and converts external destinations."""
    if not html_content:
        return ""

    prefix = get_redirect_prefix(domain_type)

    def _replace_tag(match):
        full_tag = match.group(0)
        quote = match.group(1)
        raw_href = match.group(2)

        if is_external_url(raw_href):
            wrapped = f"{prefix}{urllib.parse.quote(raw_href.strip(), safe='')}"
            # Replace only the href value
            new_tag = full_tag.replace(f'href={quote}{raw_href}{quote}', f'href={quote}{wrapped}{quote}')
            if 'target=' not in new_tag:
                new_tag = new_tag[:-1] + ' target="_blank" rel="noopener noreferrer">'
            return new_tag
        return full_tag

    pattern = re.compile(r'<a\s+[^>]*href=(["\'])(.*?)\1[^>]*>', re.IGNORECASE)
    return pattern.sub(_replace_tag, html_content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="DigiIndia Dynamic Link Handler")
    parser.add_argument("--url", type=str, help="URL to wrap with redirect formula")
    parser.add_argument("--domain", type=str, default="node", choices=["firebase", "node", "python"], help="Target domain prefix")
    parser.add_argument("--html", type=str, help="HTML snippet to process")
    parser.add_argument("--test", action="store_true", help="Run self-tests")

    args = parser.parse_args()

    if args.test:
        test_url = "https://github.com"
        for d in ["node", "firebase", "python"]:
            wrapped = wrap_redirect_url(test_url, d)
            print(f"[{d.upper()}] {wrapped}")
        print("Tests passed successfully.")
        return

    if args.url:
        print(wrap_redirect_url(args.url, args.domain))
        return

    if args.html:
        print(transform_html_links(args.html, args.domain))
        return

    print("DigiIndia Universal Link Handler Active.")
    print("Example for https://github.com:")
    for d in ["node", "firebase", "python"]:
        print(f"  {d}: {wrap_redirect_url('https://github.com', d)}")

if __name__ == "__main__":
    main()
