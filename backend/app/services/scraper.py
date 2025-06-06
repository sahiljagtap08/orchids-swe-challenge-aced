import asyncio
from typing import Optional
from .base_scraper import BaseScraper
from ..models.clone import ScrapeResult
from ..core.logging import LiveLogger
from .playwright_scraper import PlaywrightScraper
from .hyperbrowser_scraper import HyperbrowserScraper

# Other scraper imports can be added here for fallback strategies
# from .hyperbrowser_scraper import HyperBrowserScraper
# from .basic_scraper import BasicScraper

class Scraper(BaseScraper):
    """
    An orchestrating scraper that uses multiple scraping strategies
    for robustness. It tries Playwright first and falls back to
    Hyperbrowser for difficult websites.
    """
    def __init__(self, logger: Optional[LiveLogger] = None):
        self.logger = logger
        self.playwright_scraper = PlaywrightScraper(logger=logger)
        self.hyperbrowser_scraper: Optional[HyperbrowserScraper] = None
        try:
            self.hyperbrowser_scraper = HyperbrowserScraper(logger=logger)
        except ValueError:
            if self.logger:
                # This is tricky in an async context, but for a startup warning it's acceptable
                # In a real-world app, you might use a more sophisticated startup event system
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.logger.log("⚠️ HYPERBROWSER_API_KEY not set. Premium fallback scraper is disabled."))
                    else:
                        loop.run_until_complete(self.logger.log("⚠️ HYPERBROWSER_API_KEY not set. Premium fallback scraper is disabled."))
                except RuntimeError:
                     print("INFO: ⚠️ HYPERBROWSER_API_KEY not set. Premium fallback scraper is disabled.")


    async def scrape(self, url: str, viewport_width: int = 1920, viewport_height: int = 1080) -> ScrapeResult:
        """
        Scrapes a website using a fallback strategy.
        1. Try Playwright for a fast, local scrape.
        2. If it fails, use the premium Hyperbrowser service.
        """
        try:
            if self.logger:
                await self.logger.log(f"▶️ Starting scrape for {url} with standard scraper (Playwright)...")
            result = await self.playwright_scraper.scrape(url, viewport_width, viewport_height)
            if not result or not result.html or len(result.html) < 200: # Basic check for empty or error pages
                 raise ValueError("Playwright returned minimal or empty content.")
            return result
        except Exception as e:
            if self.logger:
                await self.logger.log(f"⚠️ Playwright scraping failed: {e}")
                if self.hyperbrowser_scraper:
                    await self.logger.log("   - Retrying with premium scraper (Hyperbrowser)...")
                    return await self.hyperbrowser_scraper.scrape(url, viewport_width, viewport_height)
                else:
                    await self.logger.log("   - ❌ Premium scraper is not configured. Scraping failed.")
            
            raise Exception(f"All scraping methods failed for {url}") 