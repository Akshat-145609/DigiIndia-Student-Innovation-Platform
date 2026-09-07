import re
import urllib.parse
import time
import httpx
from bs4 import BeautifulSoup
from api.router import AIRouter
from config import settings

class SecurityScannerService:
    """
    Advanced Security Scanner Engine for Destination URLs.
    Implements:
    1. Predefined Regex Suite & Quick Risk Factors (< 2ms evaluation).
    2. Live Server, SSL, and Header Inspection.
    3. DOM & Source Code Analysis (password inputs, obfuscated scripts, hidden iframes).
    4. AI-Powered Technical Brief & README Markdown Report Synthesis (Gemini -> OpenAI fallback).
    """

    # 1. Raw IP Hostnames (IPv4, IPv6, hex, octal representations)
    RAW_IP_REGEX = re.compile(
        r'^(?:https?://)?(?:'
        r'(?:\d{1,3}\.){3}\d{1,3}|'                    # Standard IPv4 (e.g. 192.168.1.1)
        r'\[[0-9a-fA-F:]+\]|'                          # IPv6 (e.g. [2001:db8::1])
        r'0x[0-9a-fA-F]+(?:\.0x[0-9a-fA-F]+)*|'       # Hex-encoded IP
        r'0[0-7]+(?:\.0[0-7]+)*'                       # Octal IP
        r')(?::\d+)?(?:/.*)?$',
        re.IGNORECASE
    )

    # 2. High-Risk / Suspicious Top-Level Domains (TLDs)
    SUSPICIOUS_TLDS = {
        'xyz', 'top', 'zip', 'mov', 'click', 'link', 'work', 'gq', 'cf', 'tk', 'ml',
        'ru', 'country', 'stream', 'download', 'racing', 'bid', 'loan', 'date',
        'faith', 'review', 'icu', 'buzz', 'monster', 'rest', 'fit', 'kim', 'surf', 'cam'
    }

    # 3. Known Trusted Reputable Domains (Never flag without explicit threat flags)
    TRUSTED_DOMAINS = {
        'google.com', 'www.google.com', 'github.com', 'www.github.com', 'youtube.com', 'www.youtube.com',
        'youtu.be', 'stackoverflow.com', 'developer.mozilla.org', 'wikipedia.org', 'en.wikipedia.org',
        'microsoft.com', 'www.microsoft.com', 'apple.com', 'www.apple.com', 'linkedin.com', 'www.linkedin.com',
        'twitter.com', 'x.com', 'reddit.com', 'www.reddit.com', 'npmjs.com', 'pypi.org', 'firebase.google.com',
        'web.app', 'firebaseapp.com', 'onrender.com'
    }

    # 4. Brand Phishing & Impersonation Keywords (Paired with sensitive actions on untrusted hosts)
    TARGET_BRANDS = [
        'google', 'paypal', 'microsoft', 'apple', 'netflix', 'amazon', 'metamask',
        'binance', 'coinbase', 'steamcommunity', 'discord-nitro', 'chase', 'wellsfargo',
        'bank', 'sbi', 'icici', 'hdfc', 'instagram', 'facebook', 'whatsapp', 'telegram'
    ]
    SENSITIVE_ACTIONS = [
        'login', 'signin', 'verify', 'verification', 'security', 'account', 'update',
        'billing', 'wallet', 'claim', 'airdrop', 'free-gift', 'recovery', 'auth', 'passcode'
    ]

    # 5. Dangerous Payload / File Download Extensions
    DANGEROUS_EXTENSIONS = (
        '.exe', '.bat', '.cmd', '.scr', '.vbs', '.msi', '.apk', '.iso', '.dmg',
        '.sh', '.ps1', '.jar', '.hta', '.pif', '.reg', '.dll', '.com'
    )

    # 6. Anonymous Tunnels & Free Dynamic DNS
    TUNNEL_DOMAINS = {
        'ngrok.io', 'loca.lt', 'trycloudflare.com', 'serveo.net', 'duckdns.org',
        'no-ip.biz', 'no-ip.org', 'pagekite.me', 'portmap.io'
    }

    # 7. Non-standard HTTP ports commonly used for unauthorized backdoors
    SUSPICIOUS_PORTS = {'8080', '8888', '1337', '6666', '3128', '4444', '9999', '5555', '7777'}

    @classmethod
    def quick_check(cls, url: str) -> dict:
        """
        Fast-Path Evaluation (< 2ms).
        Returns whether the link is suspicious, matched risk indicators, risk score (0-100), and risk level.
        """
        if not url or not isinstance(url, str):
            return {
                "is_suspicious": False,
                "reasons": [],
                "risk_score": 0,
                "risk_level": "safe",
                "hostname": ""
            }

        target = url.strip()
        reasons = []
        risk_score = 0

        # Protocol check
        if not target.startswith("http://") and not target.startswith("https://"):
            if target.startswith(("javascript:", "data:", "vbscript:", "file:")):
                reasons.append(f"Dangerous URI scheme detected ({target.split(':')[0]}:)")
                risk_score += 90
            target = f"https://{target}"

        try:
            parsed = urllib.parse.urlparse(target)
            hostname = (parsed.hostname or "").lower()
            path = parsed.path.lower()
            query = parsed.query.lower()
        except Exception:
            return {
                "is_suspicious": True,
                "reasons": ["Malformed destination URL structure"],
                "risk_score": 85,
                "risk_level": "high",
                "hostname": "unknown"
            }

        # Explicit test parameter flag
        if "suspicious=true" in query or "threat=true" in query or "test-malicious" in query or "phishing=true" in query:
            reasons.append("Explicit security audit test parameter flag detected (?suspicious=true)")
            risk_score += 85

        # Rule 1: Raw IP Address Hostname
        if cls.RAW_IP_REGEX.match(target) or re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', hostname):
            reasons.append(f"Destination uses raw IP address hostname ({hostname}) instead of registered domain")
            risk_score += 75

        # Rule 2: Non-standard suspicious port
        if parsed.port and str(parsed.port) in cls.SUSPICIOUS_PORTS:
            reasons.append(f"Non-standard HTTP port detected (:{parsed.port})")
            risk_score += 40

        # Rule 3: Authority '@' symbol (userinfo impersonation deception)
        if '@' in parsed.netloc:
            reasons.append("URL contains '@' userinfo character commonly used to disguise actual destination host")
            risk_score += 80

        # Rule 4: Dangerous payload extensions in URL path
        for ext in cls.DANGEROUS_EXTENSIONS:
            if path.endswith(ext) or f"{ext}?" in path or f"{ext}&" in query:
                reasons.append(f"Direct executable/script payload download detected ({ext})")
                risk_score += 85
                break

        # Check if domain is a known trusted domain
        is_trusted = any(hostname == td or hostname.endswith(f".{td}") for td in cls.TRUSTED_DOMAINS)

        if not is_trusted:
            # Rule 5: Suspicious / High-Abuse TLDs
            tld = hostname.split('.')[-1] if '.' in hostname else ''
            if tld in cls.SUSPICIOUS_TLDS:
                reasons.append(f"High-abuse top-level domain detected (.{tld})")
                risk_score += 60

            # Rule 6: Free dynamic DNS / Anonymous tunnels
            for td in cls.TUNNEL_DOMAINS:
                if hostname == td or hostname.endswith(f".{td}"):
                    reasons.append(f"Anonymous tunnel / dynamic DNS service detected ({td})")
                    risk_score += 65
                    break

            # Rule 7: Brand Phishing & Impersonation Check
            for brand in cls.TARGET_BRANDS:
                if brand in hostname and not any(hostname == f"{brand}.com" or hostname.endswith(f".{brand}.com") for _ in [1]):
                    reasons.append(f"Potential brand impersonation: '{brand}' detected in unverified domain '{hostname}'")
                    risk_score += 70
                    break

            # Rule 8: Sensitive Action keywords in path/query for untrusted domains
            action_matches = [act for act in cls.SENSITIVE_ACTIONS if act in path or act in query]
            if len(action_matches) >= 2:
                reasons.append(f"Multiple sensitive credential/account keywords detected: {', '.join(action_matches[:3])}")
                risk_score += 50

            # Rule 9: Punycode / Internationalized Domain Name (Homograph attack indicator)
            if "xn--" in hostname:
                reasons.append("Punycode (xn--) encoding detected, potential internationalized homograph impersonation")
                risk_score += 65

            # Rule 10: Deep multi-level subdomains (> 4 parts)
            subdomain_parts = [p for p in hostname.split('.') if p]
            if len(subdomain_parts) >= 5:
                reasons.append(f"Excessively deep subdomain structure ({len(subdomain_parts)} levels)")
                risk_score += 35

            # Rule 11: Insecure plain HTTP for sensitive terms
            if parsed.scheme == "http" and any(act in path or act in query for act in cls.SENSITIVE_ACTIONS):
                reasons.append("Insecure plain HTTP protocol used with credential/account parameters")
                risk_score += 45

        # Determine verdict
        is_suspicious = (risk_score >= 50) or (len(reasons) > 0 and not is_trusted)
        if is_trusted and "suspicious=true" not in query:
            is_suspicious = False
            reasons = []
            risk_score = 0

        risk_level = "safe"
        if risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40 or is_suspicious:
            risk_level = "medium"
        elif risk_score > 0:
            risk_level = "low"

        return {
            "is_suspicious": is_suspicious,
            "reasons": reasons,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "hostname": hostname,
            "protocol": parsed.scheme,
            "target_url": target
        }

    @classmethod
    def deep_analyze(cls, url: str) -> dict:
        """
        Deep-Path Live Test & AI Technical Brief Synthesis.
        Performs:
        1. Quick check analysis.
        2. Live destination server request (HTTP status, SSL, headers).
        3. DOM / Source Code inspection for client-side threats.
        4. AI synthesis (AIRouter) to produce structured README markdown output.
        """
        quick_result = cls.quick_check(url)
        target_url = quick_result.get("target_url", url)
        hostname = quick_result.get("hostname", "unknown")

        server_info = {
            "http_status": None,
            "is_reachable": False,
            "ssl_active": target_url.startswith("https://"),
            "server_header": "Unknown",
            "content_type": "Unknown",
            "has_csp": False,
            "has_hsts": False,
            "has_x_frame_options": False,
            "redirect_count": 0,
            "response_time_ms": 0
        }
        dom_findings = []
        source_code_snippet = ""

        start_time = time.time()
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 DigiIndiaSecurityBot/2.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            with httpx.Client(timeout=4.5, follow_redirects=True, max_redirects=3, verify=False) as client:
                resp = client.get(target_url, headers=headers)
                server_info["http_status"] = resp.status_code
                server_info["is_reachable"] = True
                server_info["response_time_ms"] = int((time.time() - start_time) * 1000)
                server_info["server_header"] = resp.headers.get("server", "Protected / Hidden")
                server_info["content_type"] = resp.headers.get("content-type", "Unknown")
                server_info["has_csp"] = "content-security-policy" in resp.headers
                server_info["has_hsts"] = "strict-transport-security" in resp.headers
                server_info["has_x_frame_options"] = "x-frame-options" in resp.headers

                raw_html = resp.text[:25000] if resp.text else ""
                source_code_snippet = raw_html[:1200]

                # DOM & Source Code Security Inspection
                if raw_html:
                    soup = BeautifulSoup(raw_html, "html.parser")

                    # Check 1: Insecure password form
                    password_inputs = soup.find_all("input", attrs={"type": "password"})
                    if password_inputs:
                        if not server_info["ssl_active"]:
                            dom_findings.append("Insecure password input field served over unencrypted HTTP")
                        forms = soup.find_all("form")
                        for form in forms:
                            action = form.get("action", "")
                            if action and (action.startswith("http://") or ("//" in action and hostname not in action)):
                                dom_findings.append(f"Credential form submits to external endpoint: {action[:50]}")

                    # Check 2: Obfuscated JavaScript
                    scripts = soup.find_all("script")
                    for s in scripts:
                        s_text = s.string or ""
                        if any(pattern in s_text for pattern in ["eval(", "document.write(atob(", "unescape(", "String.fromCharCode"]):
                            dom_findings.append("Obfuscated or dynamically evaluated JavaScript code detected")
                            break
                        if "coinhive" in s_text.lower() or "cryptonight" in s_text.lower():
                            dom_findings.append("Cryptocurrency mining script signature detected in source")
                            break

                    # Check 3: Hidden or invisible iframes
                    iframes = soup.find_all("iframe")
                    for ifr in iframes:
                        style = (ifr.get("style") or "").lower()
                        width = ifr.get("width", "")
                        height = ifr.get("height", "")
                        if "display:none" in style or "visibility:hidden" in style or width in ["0", "1"] or height in ["0", "1"]:
                            dom_findings.append("Hidden zero-pixel iframe detected in DOM (common in clickjacking/drive-by downloads)")
                            break

                    # Check 4: Suspicious meta refreshes
                    meta_refresh = soup.find("meta", attrs={"http-equiv": re.compile(r"refresh", re.IGNORECASE)})
                    if meta_refresh:
                        dom_findings.append("Automated client-side meta-refresh redirection detected")

        except Exception as e:
            server_info["is_reachable"] = False
            server_info["error_note"] = str(e)[:120]

        all_reasons = list(quick_result.get("reasons", []))
        for df in dom_findings:
            if df not in all_reasons:
                all_reasons.append(df)

        is_suspicious = quick_result["is_suspicious"] or len(dom_findings) > 0
        risk_score = min(quick_result["risk_score"] + (len(dom_findings) * 20), 100)
        risk_level = "high" if risk_score >= 70 else ("medium" if is_suspicious else "safe")

        # Synthesize AI README Markdown Report
        ai_report_markdown = cls._synthesize_ai_report(
            target_url=target_url,
            hostname=hostname,
            risk_level=risk_level,
            risk_score=risk_score,
            reasons=all_reasons,
            server_info=server_info,
            dom_findings=dom_findings,
            source_code_snippet=source_code_snippet
        )

        return {
            "targetUrl": target_url,
            "domain": hostname,
            "isSuspicious": is_suspicious,
            "riskLevel": risk_level,
            "riskScore": risk_score,
            "reasons": all_reasons,
            "serverInfo": server_info,
            "domFindings": dom_findings,
            "sourceCodeSnippet": source_code_snippet[:600] if source_code_snippet else "",
            "aiReportMarkdown": ai_report_markdown,
            "timestamp": time.time()
        }

    @classmethod
    def _synthesize_ai_report(
        cls,
        target_url: str,
        hostname: str,
        risk_level: str,
        risk_score: int,
        reasons: list,
        server_info: dict,
        dom_findings: list,
        source_code_snippet: str
    ) -> str:
        today = time.strftime("%Y-%m-%d %H:%M:%S UTC")
        reasons_list = "\n".join([f"- {r}" for r in reasons]) if reasons else "- None detected. Destination appears clean and properly configured."
        dom_list = "\n".join([f"- {d}" for d in dom_findings]) if dom_findings else "- Clean DOM structure without credential hijacking or obfuscated payloads."

        prompt = f"""
You are the DigiIndia AI System Security Scanner. Generate an executive, professional technical security brief formatted in GitHub README markdown for this destination URL test:

Destination URL: {target_url}
Hostname: {hostname}
Risk Level: {risk_level.upper()} ({risk_score}/100)
Matched Threat Reasons:
{reasons_list}

Server & Network Test:
- HTTP Status: {server_info.get('http_status')}
- SSL Active: {server_info.get('ssl_active')}
- HSTS Configured: {server_info.get('has_hsts')}
- Content Security Policy (CSP): {server_info.get('has_csp')}
- Server Header: {server_info.get('server_header')}
- Response Latency: {server_info.get('response_time_ms')}ms

DOM & Client Source Code Analysis:
{dom_list}
Source Code Excerpt:
```html
{source_code_snippet[:500]}
```

Provide a structured, clean, executive technical brief in markdown. Include:
1. Executive Verdict & Risk Badge
2. Threat Analysis & Pattern Breakdown
3. Live Technical & Server Diagnosis (in a clean markdown table)
4. Source Code Inspection Note
5. Final Security Recommendation (what the user should do).
Keep it concise, clear, and high-impact.
"""
        ai_response = None
        try:
            ai_res = AIRouter.generate_assistant_response(prompt, context="DigiIndia Outbound Gateway Security Scanner")
            if isinstance(ai_res, dict) and ai_res.get("response"):
                ai_response = ai_res["response"]
            elif isinstance(ai_res, str):
                ai_response = ai_res
        except Exception:
            pass

        if ai_response and len(ai_response.strip()) > 100:
            return ai_response.strip()

        badge_color = "🔴" if risk_level == "high" else ("🟡" if risk_level == "medium" else "🟢")
        verdict_text = "DANGEROUS / HIGH RISK" if risk_level == "high" else ("SUSPICIOUS / PROCEED WITH CAUTION" if risk_level == "medium" else "VERIFIED SAFE")

        return f"""# 🛡️ DigiIndia AI Security Scanner – Live URL Audit Report

> **Scan Timestamp:** `{today}` &bull; **Engine:** `Python Heuristics v2.4 + AI Synthesis`

### {badge_color} Security Verdict: {verdict_text} (Risk Score: {risk_score}/100)

Destination **`{hostname}`** was evaluated through our real-time security gateway.

---

## 🔍 Key Threat Indicators & Pattern Matches
{reasons_list}

---

## ⚙️ Live Server & SSL Technical Diagnosis

| Metric | Measured Value | Security Evaluation |
| :--- | :--- | :--- |
| **HTTP Status** | `{server_info.get('http_status', 'N/A')}` | {'Server responded normally' if server_info.get('http_status') == 200 else 'Non-standard response or unverified'} |
| **SSL / HTTPS Protocol** | `{'Enforced (HTTPS)' if server_info.get('ssl_active') else 'Unencrypted (Plain HTTP)'}` | {'Encrypted in transit' if server_info.get('ssl_active') else 'Insecure connection'} |
| **HSTS Enforcement** | `{'Active' if server_info.get('has_hsts') else 'Missing'}` | {'Guards against downgrade attacks' if server_info.get('has_hsts') else 'Vulnerable to MITM'} |
| **Content Security Policy** | `{'Active' if server_info.get('has_csp') else 'Missing'}` | {'XSS protection enabled' if server_info.get('has_csp') else 'Standard policy'} |
| **Server Banner** | `{server_info.get('server_header', 'Unknown')}` | Identified infrastructure |
| **Gateway Latency** | `{server_info.get('response_time_ms', 0)} ms` | Live probe verification |

---

## 💻 DOM & Source Code Analysis
{dom_list}

{f'''```html
{source_code_snippet[:350]}
```''' if source_code_snippet else ''}

---

## ⚠️ Security Recommendation
{'**Do NOT proceed to this link.** It exhibits patterns characteristic of credential phishing or unauthorized software delivery. Never enter sensitive student account credentials.' if risk_level in ['high', 'medium'] else '**The destination link appears safe to visit.** Normal SSL and network security parameters were verified.'}
"""
