import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

try:
    from .database import init_db
    from .routes import requirements, templates, reports, dashboard
    from .services.gemini_service import GeminiService
except (ImportError, ValueError):
    from database import init_db
    from routes import requirements, templates, reports, dashboard
    from services.gemini_service import GeminiService

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Yathi Pumps PDI Automation",
    description="Automated PDI Report Generation for Yathi Pumps (Customers: Havells, Crompton, KBS, KOEL) with Gemini API, Excel Template Preservation, and n8n Email Integration",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(requirements.router)
app.include_router(templates.router)
app.include_router(reports.router)
app.include_router(dashboard.router)

@app.get("/api/health")
async def health_check():
    ai = GeminiService()
    gemini_status = ai.check_health()
    return {
        "status": "healthy",
        "service": "Havells PDI Automation Backend",
        "gemini": gemini_status
    }

# Mount frontend production build if available
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Do not intercept /api calls
        if full_path.startswith("api"):
            return None
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
