import asyncio
import base64
import os
from typing import Optional

from playwright.async_api import async_playwright
from hyperbrowser import AsyncHyperbrowser

from ..core.config import settings
from ..models.clone import ScrapeResult, ScrapeMetadata
from .base_scraper import BaseScraper
from ..core.logging import LiveLogger

class HyperbrowserScraper(BaseScraper):
    """
    A scraper that uses the Hyperbrowser.ai service to bypass blocking
    and handle complex websites. It acts as a premium fallback.
    """
    def __init__(self, logger: Optional[LiveLogger] = None):
        self.logger = logger
        # Load key from settings or environment
        api_key = settings.hyperbrowser_api_key or os.getenv("HYPERBROWSER_API_KEY")
        if not api_key:
            raise ValueError("HYPERBROWSER_API_KEY must be configured to use this scraper.")
        self.client = AsyncHyperbrowser(api_key=api_key)

    async def scrape(self, url: str, viewport_width: int = 1920, viewport_height: int = 1080) -> ScrapeResult:
        """
        Scrapes a website using a remote Hyperbrowser session.

        Args:
            url: The URL to scrape.
            viewport_width: The width of the browser viewport.
            viewport_height: The height of the browser viewport.

        Returns:
            A ScrapeResult object containing the scraped data.
        """
        if self.logger:
            await self.logger.log(f"💎 Using premium scraper: Hyperbrowser.ai for {url}")

        session = None
        try:
            session = await self.client.sessions.create()
            ws_endpoint = session.ws_endpoint

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(ws_endpoint)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()

                await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                
                if self.logger:
                    await self.logger.log("   - Page loaded, waiting for dynamic content...")
                await page.wait_for_timeout(5000) # Wait for SPA to hydrate

                html_content = await page.content()
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

                # Extract metadata
                title = await page.title()
                
                await browser.close()

            # Stop the session cleanly
            await self.client.sessions.stop(session.id)
            session = None

            if self.logger:
                await self.logger.log(f"   - ✅ Hyperbrowser scrape successful for {url}")

            # Note: Asset/CSS extraction is simplified here. The primary purpose
            # of this scraper is to get the core HTML and a perfect screenshot
            # from difficult-to-scrape sites.
            return ScrapeResult(
                url=url,
                html=html_content,
                css="", # Let the vision model handle styling from the screenshot
                screenshot=screenshot_b64,
                assets=[],
                metadata=ScrapeMetadata(
                    title=title,
                    description="",
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                    load_time=0, # Not easily available
                    assets_count=0
                )
            )

        except Exception as e:
            if self.logger:
                await self.logger.log(f"   - ❌ Hyperbrowser scrape failed: {str(e)}")
            # Ensure session is stopped even if an error occurs
            if session:
                try:
                    await self.client.sessions.stop(session.id)
                except Exception as stop_e:
                    if self.logger:
                        await self.logger.log(f"   - ⚠️ Failed to stop hanging Hyperbrowser session: {stop_e}")
            raise e 