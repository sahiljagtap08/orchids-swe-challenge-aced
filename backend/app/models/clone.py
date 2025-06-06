from pydantic import BaseModel, HttpUrl, ConfigDict, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class CloneStatus(str, Enum):
    PENDING = "pending"
    SCRAPING = "scraping"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CloneRequest(BaseModel):
    url: str
    model: str = "agentic"
    full_site: bool = False  # New: Clone entire website
    max_pages: int = 50      # Limit for safety
    include_assets: bool = True  # Download all assets


class ScrapeMetadata(BaseModel):
    title: str
    description: str
    viewport_width: int
    viewport_height: int
    load_time: float
    screenshot_url: Optional[str] = None
    assets_count: int = 0


class ScrapeResult(BaseModel):
    url: str
    html: str
    css: Optional[str] = None
    screenshot: Optional[str] = None  # base64 encoded
    metadata: ScrapeMetadata
    assets: List[Dict[str, Any]] = []


class LLMCloneResult(BaseModel):
    html: str
    css: Optional[str] = None
    reasoning: str
    model_used: str
    processing_time: float


class PageCloneResult(BaseModel):
    """Result for a single page within a full site clone"""
    url: str
    path: str
    html: str
    css: Optional[str] = None
    screenshot: Optional[str] = None
    assets: List[Dict[str, Any]] = []
    metadata: ScrapeMetadata


class FullSiteCloneResult(BaseModel):
    """Result for complete website cloning"""
    base_url: str
    pages: List[PageCloneResult]
    assets: List[Dict[str, Any]]  # All unique assets
    sitemap: List[str]            # All discovered URLs
    clone_time: float
    total_pages: int
    total_assets: int
    model_used: str


class CloneJobResponse(BaseModel):
    job_id: str
    url: str
    model: str
    status: str  # pending, discovering, scraping, processing, completed, failed
    progress: Optional[str] = None
    error: Optional[str] = None
    result: Optional[LLMCloneResult] = None
    full_site_result: Optional[FullSiteCloneResult] = None  # New
    created_at: datetime
    updated_at: datetime 