from abc import ABC, abstractmethod

from ..models.clone import ScrapeResult


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    @abstractmethod
    async def scrape(
        self, url: str, viewport_width: int = 1920, viewport_height: int = 1080
    ) -> ScrapeResult:
        """Scrapes a website and returns the result."""
        pass 