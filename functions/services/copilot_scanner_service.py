import re

class CoPilotBugScanner:
    """
    AI Project Co-Pilot & Bug Scanner.
    Performs static analysis to detect hardcoded API keys/secrets, security vulnerabilities,
    and memory/resource leaks in student source code.
    """

    SECRET_PATTERNS = [
        (r'sk-[a-zA-Z0-9]{32,}', "OpenAI Secret Key"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
        (r'AIzaSy[a-zA-Z0-9_-]{33}', "Firebase/Google API Key"),
        (r'SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}', "SendGrid API Key"),
        (r'sk_live_[0-9a-zA-Z]{24}', "Stripe Live Secret Key"),
        (r'-----BEGIN PRIVATE KEY-----', "RSA Private Key"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded Plaintext Password")
    ]

    VULNERABILITY_PATTERNS = [
        (r'\beval\s*\(', "Unsanitized eval() Execution", "HIGH"),
        (r'\bexec\s*\(', "Unsanitized exec() Execution", "HIGH"),
        (r'SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*%s', "Potential SQL Injection Vulnerability", "HIGH"),
        (r'innerHTML\s*=\s*.*', "Potential DOM XSS Vulnerability", "MEDIUM"),
        (r'document\.write\s*\(', "Unsafe document.write() Invocation", "LOW")
    ]

    LEAK_PATTERNS = [
        (r'open\s*\(.*?\)(?!\s*with)', "Unclosed File Resource Leak", "MEDIUM"),
        (r'while\s*\(\s*True\s*\):', "Potential Infinite Loop Risk without explicit break condition", "MEDIUM"),
        (r'requests\.get\s*\([^)]*?\)(?!\s*,\s*timeout=)', "HTTP Request Missing Explicit Timeout", "LOW")
    ]

    @classmethod
    def scan_code(cls, code_content: str, filename: str = "main.py") -> dict:
        if not code_content:
            return {"filename": filename, "totalIssues": 0, "findings": []}

        findings = []

        # 1. Scan for Secrets & Hardcoded Keys
        for pattern, secret_type in cls.SECRET_PATTERNS:
            matches = re.finditer(pattern, code_content)
            for m in matches:
                line_no = code_content[:m.start()].count('\n') + 1
                findings.append({
                    "category": "HARDCODED_SECRET",
                    "severity": "CRITICAL",
                    "issue": f"Exposed {secret_type}",
                    "line": line_no,
                    "remediation": "Move hardcoded secret to environment variables (.env file)."
                })

        # 2. Scan for Security Vulnerabilities
        for pattern, vuln_name, severity in cls.VULNERABILITY_PATTERNS:
            matches = re.finditer(pattern, code_content, re.IGNORECASE)
            for m in matches:
                line_no = code_content[:m.start()].count('\n') + 1
                findings.append({
                    "category": "SECURITY_VULNERABILITY",
                    "severity": severity,
                    "issue": vuln_name,
                    "line": line_no,
                    "remediation": "Sanitize input parameters and use parameterized queries or safe APIs."
                })

        # 3. Scan for Memory & Resource Leaks
        for pattern, leak_name, severity in cls.LEAK_PATTERNS:
            matches = re.finditer(pattern, code_content)
            for m in matches:
                line_no = code_content[:m.start()].count('\n') + 1
                findings.append({
                    "category": "RESOURCE_LEAK",
                    "severity": severity,
                    "issue": leak_name,
                    "line": line_no,
                    "remediation": "Use context managers ('with' block) or add explicit timeouts."
                })

        critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")

        code_health_score = max(0, 100 - (critical_count * 30 + high_count * 15 + len(findings) * 5))

        return {
            "filename": filename,
            "codeHealthScore": code_health_score,
            "totalIssues": len(findings),
            "criticalIssues": critical_count,
            "highIssues": high_count,
            "findings": findings,
            "summary": f"Co-Pilot Bug Scan finished. Code Health Score: {code_health_score}/100. Total Issues: {len(findings)}."
        }
