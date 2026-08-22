import os
from fastapi import FastAPI
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

# Serve public web assets if run directly
public_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))
if os.path.exists(public_path):
    app.mount("/", StaticFiles(directory=public_path, html=True), name="public")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=settings.PORT)