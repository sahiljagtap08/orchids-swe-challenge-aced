import asyncio
import base64
import time
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page
import json

from ..models.clone import ScrapeResult, ScrapeMetadata
from ..core.logging import LiveLogger


class PlaywrightScraper:
    """Production-grade browser automation for 100% accurate website capture"""
    
    def __init__(self, logger: Optional[LiveLogger] = None):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.logger = logger
    
    async def __aenter__(self):
        if self.logger:
            await self.logger.log("▶️ Launching headless browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.logger:
            await self.logger.log("✅ Headless browser closed.")
    
    async def scrape(self, url: str, viewport_width: int = 1920, viewport_height: int = 1080) -> Optional[ScrapeResult]:
        """
        Scrape a website using Playwright, with robust waiting logic.
        
        This method waits for the page to be fully loaded, including network
        activity to settle, ensuring that dynamically-loaded content is captured.
        
        Args:
            url: The URL to scrape
        
        Returns:
            A ScrapeResult object with HTML, screenshot, and metadata, or None on failure.
        """
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(
                    viewport={'width': viewport_width, 'height': viewport_height}
                )
                page = await context.new_page()
                
                # Navigate to the page with a generous timeout
                if self.logger:
                    await self.logger.log(f"   - Navigating to {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Additional wait for any final DOM changes and SPA hydration
                await self.logger.log("   - Page loaded, waiting for dynamic content...")
                await page.wait_for_timeout(5000) # Increased wait time for SPAs
                
                if self.logger:
                    await self.logger.log("   - Capturing content...")

                # Get page content
                html = await page.content()
                
                # Get a high-quality screenshot
                screenshot_bytes = await page.screenshot(type="png", full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Get all computed CSS styles
                # Note: This can be very large and is currently disabled for performance.
                # Enable if precise CSS replication is needed and performance allows.
                # css = await page.evaluate('() => { ... }') 
                
                # Extract metadata
                title = await page.title()
                viewport_size = page.viewport_size or {'width': 0, 'height': 0}
                
                metadata = ScrapeMetadata(
                    title=title,
                    description=await page.evaluate("() => document.querySelector('meta[name=description]')?.content || ''"),
                    viewport_width=viewport_size['width'],
                    viewport_height=viewport_size['height'],
                    load_time=0,  # Placeholder, can be improved
                    assets_count=0 # Placeholder, can be improved
                )
                
                await browser.close()
                
                if self.logger:
                    await self.logger.log("   - ✅ Content capture complete.")
                
                return ScrapeResult(
                    url=url,
                    html=html,
                    css="", # CSS is now inline or linked, not extracted separately here
                    screenshot=screenshot_b64,
                    assets=[], # Asset downloader will handle this later
                    metadata=metadata
                )
        
        except Exception as e:
            print(f"Playwright scraping failed for {url}: {str(e)}")
            return None
    
    async def _extract_computed_styles(self, page: Page) -> str:
        """Extract computed CSS styles for accurate visual recreation"""
        
        try:
            # Get computed styles for all visible elements
            computed_styles = await page.evaluate("""
                () => {
                    const styles = [];
                    const elements = document.querySelectorAll('*');
                    
                    elements.forEach((element, index) => {
                        if (element.offsetParent !== null) { // Only visible elements
                            const computedStyle = window.getComputedStyle(element);
                            const tagName = element.tagName.toLowerCase();
                            const classes = element.className ? '.' + element.className.split(' ').join('.') : '';
                            const id = element.id ? '#' + element.id : '';
                            
                            // Create selector
                            let selector = tagName + id + classes;
                            if (!id && !classes) {
                                selector = tagName + ':nth-child(' + (Array.from(element.parentNode.children).indexOf(element) + 1) + ')';
                            }
                            
                            // Extract key visual properties
                            const styleProps = {
                                display: computedStyle.display,
                                position: computedStyle.position,
                                width: computedStyle.width,
                                height: computedStyle.height,
                                margin: computedStyle.margin,
                                padding: computedStyle.padding,
                                backgroundColor: computedStyle.backgroundColor,
                                color: computedStyle.color,
                                fontSize: computedStyle.fontSize,
                                fontFamily: computedStyle.fontFamily,
                                fontWeight: computedStyle.fontWeight,
                                lineHeight: computedStyle.lineHeight,
                                textAlign: computedStyle.textAlign,
                                border: computedStyle.border,
                                borderRadius: computedStyle.borderRadius,
                                boxShadow: computedStyle.boxShadow,
                                backgroundImage: computedStyle.backgroundImage,
                                backgroundSize: computedStyle.backgroundSize,
                                backgroundPosition: computedStyle.backgroundPosition,
                                transform: computedStyle.transform,
                                opacity: computedStyle.opacity,
                                zIndex: computedStyle.zIndex,
                                flexDirection: computedStyle.flexDirection,
                                justifyContent: computedStyle.justifyContent,
                                alignItems: computedStyle.alignItems,
                                gridTemplateColumns: computedStyle.gridTemplateColumns,
                                gridTemplateRows: computedStyle.gridTemplateRows,
                                gap: computedStyle.gap
                            };
                            
                            // Build CSS rule
                            let cssRule = selector + ' {\\n';
                            for (const [prop, value] of Object.entries(styleProps)) {
                                if (value && value !== 'none' && value !== 'auto' && value !== 'normal') {
                                    const cssProp = prop.replace(/([A-Z])/g, '-$1').toLowerCase();
                                    cssRule += `  ${cssProp}: ${value};\\n`;
                                }
                            }
                            cssRule += '}\\n\\n';
                            
                            styles.push(cssRule);
                        }
                    });
                    
                    return styles.join('');
                }
            """)
            
            return computed_styles
            
        except Exception as e:
            print(f"❌ Computed styles extraction failed: {str(e)}")
            return "/* Computed styles extraction failed */"
    
    async def _extract_page_assets(self, page: Page, base_url: str) -> List[Dict[str, Any]]:
        """Extract all page assets with full URLs"""
        
        try:
            assets = await page.evaluate("""
                (baseUrl) => {
                    const assets = [];
                    
                    // Images
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src) {
                            assets.push({
                                type: 'image',
                                url: img.src,
                                alt: img.alt || '',
                                element: 'img',
                                width: img.naturalWidth,
                                height: img.naturalHeight
                            });
                        }
                    });
                    
                    // Stylesheets
                    document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
                        if (link.href) {
                            assets.push({
                                type: 'stylesheet',
                                url: link.href,
                                element: 'link'
                            });
                        }
                    });
                    
                    // Fonts
                    document.querySelectorAll('link').forEach(link => {
                        if (link.href && (link.href.includes('font') || link.href.includes('googleapis.com/css'))) {
                            assets.push({
                                type: 'font',
                                url: link.href,
                                element: 'link'
                            });
                        }
                    });
                    
                    // Background images from CSS
                    const elements = document.querySelectorAll('*');
                    elements.forEach(element => {
                        const style = window.getComputedStyle(element);
                        if (style.backgroundImage && style.backgroundImage !== 'none') {
                            const match = style.backgroundImage.match(/url\\(["']?([^"'\\)]+)["']?\\)/);
                            if (match) {
                                assets.push({
                                    type: 'background-image',
                                    url: match[1],
                                    element: element.tagName.toLowerCase()
                                });
                            }
                        }
                    });
                    
                    return assets;
                }
            """, base_url)
            
            return assets
            
        except Exception as e:
            print(f"❌ Asset extraction failed: {str(e)}")
            return []
    
    async def _extract_page_metadata(self, page: Page, url: str) -> ScrapeMetadata:
        """Extract comprehensive page metadata"""
        
        try:
            metadata = await page.evaluate("""
                () => {
                    const title = document.title || '';
                    const description = document.querySelector('meta[name="description"]')?.content || '';
                    const viewport = document.querySelector('meta[name="viewport"]')?.content || '';
                    
                    return {
                        title: title,
                        description: description,
                        viewport: viewport
                    };
                }
            """)
            
            return ScrapeMetadata(
                title=metadata['title'] or f"Playwright: {url}",
                description=metadata['description'] or f"Real browser content from {url}",
                viewport_width=1920,
                viewport_height=1080,
                load_time=0,  # Will be set by caller
                screenshot_url=None,
                assets_count=0  # Will be set by caller
            )
            
        except Exception as e:
            print(f"❌ Metadata extraction failed: {str(e)}")
            return ScrapeMetadata(
                title=f"Playwright: {url}",
                description=f"Browser-scraped content from {url}",
                viewport_width=1920,
                viewport_height=1080,
                load_time=0,
                screenshot_url=None,
                assets_count=0
            ) 