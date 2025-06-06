from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
import uuid
import json
import asyncio
from datetime import datetime
import os

from ..services.scraper import Scraper
from ..services.llm import LLMService
from ..services.full_site_scraper import FullSiteScraper
from ..models.clone import CloneRequest, CloneJobResponse
from ..core.logging import LiveLogger

router = APIRouter()

# In-memory storage for demo (replace with database in production)
clone_jobs: Dict[str, Dict[str, Any]] = {}

# Live logs storage
live_logs: Dict[str, List[str]] = {}  # job_id -> list of log messages


class CloneJobCreate(BaseModel):
    url: str
    model: str = "agentic"  # agentic, fast, precise, economic
    full_site: bool = False  # New: Enable full website cloning
    max_pages: int = 20      # Limit for full site cloning
    include_assets: bool = True  # Download all assets


@router.post("/clone", response_model=CloneJobResponse)
async def create_clone_job(
    request: CloneJobCreate,
    background_tasks: BackgroundTasks
):
    """Create a new website cloning job (single page or full site)"""
    
    job_id = str(uuid.uuid4())
    
    # Initialize job data
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "url": request.url,
        "model": request.model,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "progress": "Initializing...",
        "result": None,
        "full_site_result": None,
        "error": None
    }
    clone_jobs[job_id] = job_data
    
    # Start background processing
    clone_request = CloneRequest(**request.dict())
    background_tasks.add_task(process_clone_job, job_id, clone_request)
    
    return CloneJobResponse(**job_data)


@router.get("/clone/{job_id}", response_model=CloneJobResponse)
async def get_clone_job(job_id: str):
    """Get the status and result of a cloning job"""
    
    if job_id not in clone_jobs:
        raise HTTPException(status_code=404, detail="Clone job not found")
    
    job_data = clone_jobs[job_id]
    return CloneJobResponse(**job_data)


@router.get("/clone", response_model=list[CloneJobResponse])
async def list_clone_jobs():
    """List all cloning jobs (for demo purposes)"""
    
    return [CloneJobResponse(**job_data) for job_data in clone_jobs.values()]


@router.get("/clone/{job_id}/logs")
async def stream_clone_logs(job_id: str):
    """Streams live logs for a cloning job using SSE."""
    if job_id not in clone_jobs:
        raise HTTPException(status_code=404, detail="Clone job not found")
    
    async def event_generator():
        async for log in LiveLogger.subscribe(job_id):
            yield log

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def process_clone_job(job_id: str, request: CloneRequest):
    """Unified background task for all cloning jobs"""
    logger = LiveLogger(job_id)
    
    def update_status(status: str, progress: str):
        clone_jobs[job_id].update({
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow()
        })

    try:
        if request.full_site:
            await logger.log("🚀 Initializing full site clone...")
            update_status("discovering", "🕷️ Discovering all pages and routes...")
            full_site_scraper = FullSiteScraper(logger=logger)
            full_site_result = await full_site_scraper.clone_full_website(request)
            
            # Update job with full site result
            clone_jobs[job_id]["full_site_result"] = full_site_result.dict()
        else:
            await logger.log("🚀 Initializing single page clone...")
            update_status("scraping", "📄 Scraping single page...")
            scraper_service = Scraper(logger=logger)
            scrape_result = await scraper_service.scrape(request.url)
            if not scrape_result:
                raise Exception("Failed to scrape website")
            
            update_status("processing", f"🧠 Generating clone with {request.model} AI...")
            llm_service = LLMService()
            clone_result = await llm_service.clone_website(
                scrape_data=scrape_result, model=request.model, logger=logger
            )
            clone_jobs[job_id]["result"] = clone_result.dict()
        
        update_status("completed", "✅ Clone completed!")
        
    except Exception as e:
        error_message = f"Failed: {str(e)}"
        await logger.log(f"❌ {error_message}")
        update_status("failed", error_message)
        clone_jobs[job_id]["error"] = str(e)
    finally:
        await logger.log("[END]")


@router.get("/clone/{job_id}/download")
async def download_cloned_site(job_id: str):
    """Download the complete cloned site as a ZIP file"""
    
    if job_id not in clone_jobs:
        raise HTTPException(status_code=404, detail="Clone job not found")
    
    job_data = clone_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Clone job not completed")
    
    if job_data.get("full_site_result"):
        # Full site download
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            full_site_result = job_data["full_site_result"]
            written_paths = set()

            for page in full_site_result.get("pages", []):
                path = page.get("path", "/")

                # Normalize path to create a file path
                file_path = path.strip('/')
                
                if not file_path:
                    # Root path, e.g., /
                    file_path = "index.html"
                elif path.endswith('/'):
                    # Directory-like URL, e.g., /about/
                    file_path = f"{file_path}/index.html"
                elif not os.path.splitext(file_path)[1]:
                    # No file extension, e.g., /about
                    file_path = f"{file_path}.html"

                if file_path in written_paths:
                    continue
                
                zip_file.writestr(file_path, page["html"])
                written_paths.add(file_path)

            # Add sitemap
            sitemap_content = "\n".join(full_site_result.get("sitemap", []))
            if sitemap_content:
                zip_file.writestr("sitemap.txt", sitemap_content)
        
        zip_buffer.seek(0)
        
        from fastapi.responses import Response
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=cloned_site_{job_id}.zip"}
        )
    
    else:
        # Single page download
        result = job_data["result"]
        html_content = result["html"]
        
        from fastapi.responses import Response
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=clone_{job_id}.html"}
        ) 