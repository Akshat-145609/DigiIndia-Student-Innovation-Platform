import os
from fastapi import FastAPI
from fastapi.responses import Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings


from routes.auth_routes import router as auth_router
from routes.student_routes import router as student_router
from routes.project_routes import router as project_router
from routes.verification_routes import router as verification_router
from routes.api_key_routes import router as api_key_router
from routes.network_routes import router as network_router
from routes.message_routes import router as message_router
from routes.search_routes import router as search_router
from routes.ai_routes import router as ai_router
from routes.admin_routes import router as admin_router
from routes.comment_routes import router as comment_router

app = FastAPI(
    title=settings.APP_NAME,
    description="DigiIndia – Student Innovation Platform Backend API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Setup
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(student_router, prefix=api_v1_prefix)
app.include_router(project_router, prefix=api_v1_prefix)
app.include_router(comment_router, prefix=api_v1_prefix)
app.include_router(verification_router, prefix=api_v1_prefix)
app.include_router(api_key_router, prefix=api_v1_prefix)
app.include_router(network_router, prefix=api_v1_prefix)
app.include_router(message_router, prefix=api_v1_prefix)
app.include_router(search_router, prefix=api_v1_prefix)
app.include_router(ai_router, prefix=api_v1_prefix)
app.include_router(admin_router, prefix=api_v1_prefix)
from routes.websocket_routes import router as ws_router
app.include_router(ws_router, prefix=api_v1_prefix)



@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "features": {
            "ai": settings.ENABLE_AI,
            "email": settings.ENABLE_EMAIL,
            "notifications": settings.ENABLE_NOTIFICATIONS
        }
    }

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots_txt():
    content = """User-agent: *
Allow: /
Allow: /search.html
Allow: /profile.html
Allow: /project.html
Allow: /index.html
Allow: /CreateAccount.html
Allow: /Admin.html
Allow: /*?spn=*
Allow: /*?q=*
Allow: /*?id=*

Sitemap: https://digiindia-student-platform.onrender.com/sitemap.xml
Sitemap: https://digiindia-studentcollaboration.web.app/sitemap.xml
"""
    return content

@app.get("/sitemap.xml")
def get_sitemap_xml():
    from api.providers.firebase import FirestoreRepository
    students_repo = FirestoreRepository("students")
    projects_repo = FirestoreRepository("projects")

    students = students_repo.query()
    projects = projects_repo.query()

    urls = [
        "https://digiindia-student-platform.onrender.com/",
        "https://digiindia-student-platform.onrender.com/search.html",
        "https://digiindia-student-platform.onrender.com/index.html",
        "https://digiindia-student-platform.onrender.com/CreateAccount.html",
        "https://digiindia-student-platform.onrender.com/Admin.html",
    ]

    for s in students:
        spn = s.get("spn")
        if spn:
            urls.append(f"https://digiindia-student-platform.onrender.com/profile.html?spn={spn}")

    for p in projects:
        pid = p.get("projectId")
        if pid:
            urls.append(f"https://digiindia-student-platform.onrender.com/project.html?id={pid}")

    tech_stacks = ["python", "javascript", "react", "fastapi", "ai", "machine-learning", "flutter", "java", "cpp"]
    for t in tech_stacks:
        urls.append(f"https://digiindia-student-platform.onrender.com/search.html?q={t}")

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for u in urls:
        xml_lines.append(f'  <url><loc>{u}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')
    xml_lines.append('</urlset>')

    return Response(content="\n".join(xml_lines), media_type="application/xml")

# Mount Static Front-End (public folder)
public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if os.path.exists(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)