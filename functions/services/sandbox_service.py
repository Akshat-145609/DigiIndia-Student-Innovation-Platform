import base64

class SandboxEngine:
    """
    Interactive AI Project Sandbox / Playground Engine.
    Compiles client HTML5, CSS3, and JavaScript snippets into an isolated sandbox bundle.
    """

    @classmethod
    def generate_sandbox_bundle(cls, html_code: str = "", css_code: str = "", js_code: str = "") -> dict:
        combined_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DigiIndia AI Sandbox Preview</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 15px; font-family: system-ui, -apple-system, sans-serif; }}
        {css_code}
    </style>
</head>
<body>
    {html_code or '<div class="alert alert-info">Live AI Sandbox Running...</div>'}
    <script>
        try {{
            {js_code}
        }} catch(e) {{
            document.body.insertAdjacentHTML('beforeend', '<div class="alert alert-danger mt-3">Runtime Error: ' + e.message + '</div>');
        }}
    </script>
</body>
</html>"""

        encoded = base64.b64encode(combined_html.encode('utf-8')).decode('utf-8')
        data_uri = f"data:text/html;base64,{encoded}"

        return {
            "status": "ready",
            "dataUri": data_uri,
            "htmlSnippet": combined_html,
            "sandboxMode": "WebContainer Client Sandbox"
        }
