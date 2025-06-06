import asyncio
import os
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

from ..models.clone import (
    ScrapeResult, PageCloneResult, FullSiteCloneResult, 
    ScrapeMetadata, CloneRequest
)
from .site_crawler import SiteCrawler
from .scraper import Scraper
from .asset_downloader import AssetDownloader
from .llm import LLMService
from ..core.logging import LiveLogger


class FullSiteScraper:
    """Complete website cloning system - discovers, scrapes, and clones entire websites"""
    
    def __init__(self, logger: LiveLogger):
        self.crawler = None
        self.scraper = Scraper(logger=logger)
        self.asset_downloader = AssetDownloader()
        self.llm_service = LLMService(logger=logger)
        self.logger = logger
        
    async def clone_full_website(self, request: CloneRequest) -> FullSiteCloneResult:
        """
        Clone an entire website with all pages, routes, and assets
        
        Args:
            request: Clone request with URL, model, and options
            
        Returns:
            Complete website clone with all pages and assets
        """
        
        start_time = time.time()
        base_url = request.url
        
        await self.logger.log(f"🚀 Starting FULL WEBSITE CLONING for {base_url}")
        await self.logger.log(f"📋 Options: Model={request.model}, MaxPages={request.max_pages}, IncludeAssets={request.include_assets}")
        
        try:
            # Step 1: Discover all pages
            await self.logger.log("\n🕷️ Phase 1: Site Discovery")
            all_urls = await self._discover_all_pages(base_url, request.max_pages)
            
            # Step 2: Scrape all pages
            await self.logger.log(f"\n📄 Phase 2: Multi-Page Scraping ({len(all_urls)} pages)")
            scraped_pages = await self._scrape_all_pages(all_urls)
            
            # Step 3: Download and embed assets
            if request.include_assets:
                await self.logger.log(f"\n📦 Phase 3: Asset Processing")
                await self._process_all_assets(scraped_pages)
            else:
                await self.logger.log("\n📦 Phase 3: Asset Processing (Skipped)")
            
            # Step 4: AI clone generation
            await self.logger.log(f"\n🧠 Phase 4: AI Cloning with {request.model}")
            cloned_pages = await self._generate_ai_clones(scraped_pages, request.model)
            
            # Step 5: Fix internal links
            await self.logger.log(f"\n🔗 Phase 5: Link Processing")
            self._fix_internal_links(cloned_pages)
            
            clone_time = time.time() - start_time
            
            # Collect all unique assets
            all_assets = []
            for page in cloned_pages:
                all_assets.extend(page.assets)
            
            # Remove duplicates
            unique_assets = []
            seen_urls = set()
            for asset in all_assets:
                asset_url = asset.get('url', '')
                if asset_url and asset_url not in seen_urls:
                    unique_assets.append(asset)
                    seen_urls.add(asset_url)
            
            result = FullSiteCloneResult(
                base_url=base_url,
                pages=cloned_pages,
                assets=unique_assets,
                sitemap=all_urls,
                clone_time=clone_time,
                total_pages=len(cloned_pages),
                total_assets=len(unique_assets),
                model_used=request.model
            )
            
            await self.logger.log(f"\n✅ FULL WEBSITE CLONING COMPLETED!")
            await self.logger.log(f"📊 Results: {len(cloned_pages)} pages, {len(unique_assets)} assets, {clone_time:.2f}s")
            
            return result
            
        except Exception as e:
            await self.logger.log(f"❌ Full site cloning failed: {str(e)}")
            raise e
    
    async def _discover_all_pages(self, base_url: str, max_pages: int) -> List[str]:
        """Discover all pages on the website"""
        
        self.crawler = SiteCrawler(max_pages=max_pages)
        all_urls = await self.crawler.discover_all_pages(base_url)
        
        await self.logger.log(f"✅ Site discovery: {len(all_urls)} pages found")
        for i, url in enumerate(all_urls[:5]):  # Show first 5
            await self.logger.log(f"   - {url}")
        if len(all_urls) > 5:
            await self.logger.log(f"   ... and {len(all_urls) - 5} more pages")
        
        return all_urls
    
    async def _scrape_all_pages(self, urls: List[str]) -> List[ScrapeResult]:
        """Scrape all discovered pages"""
        
        scraped_pages = []
        
        # Process pages in small batches to avoid overwhelming servers
        batch_size = 3
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            await self.logger.log(f"📄 Scraping batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
            
            # Process batch in parallel
            tasks = [self.scraper.scrape(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, batch_results):
                if isinstance(result, ScrapeResult) and result:
                    scraped_pages.append(result)
                    await self.logger.log(f"   ✅ Scraped: {url} ({len(result.html)} chars)")
                else:
                    await self.logger.log(f"   ❌ FAILED to scrape: {url}")
            
            # Be respectful - small delay between batches
            await asyncio.sleep(1.0)
        
        await self.logger.log(f"✅ Multi-page scraping: {len(scraped_pages)}/{len(urls)} pages scraped successfully")
        return scraped_pages
    
    async def _process_all_assets(self, scraped_pages: List[ScrapeResult]):
        """Download and embed assets for all pages"""
        
        await self.logger.log("📦 Processing assets for all pages...")
        
        for i, page in enumerate(scraped_pages):
            await self.logger.log(f"📦 Processing assets for page {i+1}/{len(scraped_pages)}: {page.url}")
            
            try:
                # Download and embed assets
                enhanced_html = await self.asset_downloader.download_and_embed_assets(
                    page.html, page.url
                )
                
                # Update the page HTML with embedded assets
                page.html = enhanced_html
                
                await self.logger.log(f"   ✅ Assets processed for {page.url}")
                
            except Exception as e:
                await self.logger.log(f"   ⚠️ Asset processing failed for {page.url}: {str(e)}")
            
            # Small delay to be respectful
            await asyncio.sleep(0.5)
    
    async def _generate_ai_clones(self, scraped_pages: List[ScrapeResult], model: str) -> List[PageCloneResult]:
        """Generate AI clones for all scraped pages"""
        
        cloned_pages = []
        
        for i, page in enumerate(scraped_pages):
            await self.logger.log(f"🧠 AI cloning page {i+1}/{len(scraped_pages)}: {page.url}")
            
            try:
                # Generate AI clone (pass logger to LLM service)
                llm_result = await self.llm_service.clone_website(page, model, self.logger)
                
                # Convert to PageCloneResult
                parsed_url = urlparse(page.url)
                page_path = parsed_url.path or '/'
                
                clone_page = PageCloneResult(
                    url=page.url,
                    path=page_path,
                    html=llm_result.html,
                    css=llm_result.css,
                    screenshot=page.screenshot,
                    assets=page.assets,
                    metadata=page.metadata
                )
                
                cloned_pages.append(clone_page)
                await self.logger.log(f"   ✅ AI clone generated ({len(llm_result.html)} chars)")
                
            except Exception as e:
                await self.logger.log(f"   ❌ AI cloning failed for {page.url}: {str(e)}")
                # Create fallback page
                parsed_url = urlparse(page.url)
                fallback_page = PageCloneResult(
                    url=page.url,
                    path=parsed_url.path or '/',
                    html=page.html,  # Use original HTML as fallback
                    css=page.css,
                    screenshot=page.screenshot,
                    assets=page.assets,
                    metadata=page.metadata
                )
                cloned_pages.append(fallback_page)
            
            # Small delay between AI calls
            await asyncio.sleep(0.5)
        
        await self.logger.log(f"✅ AI cloning: {len(cloned_pages)} pages processed")
        return cloned_pages
    
    def _fix_internal_links(self, cloned_pages: List[PageCloneResult]):
        """Fix internal links to work within the cloned site for offline browsing."""
        
        self.logger.log("🔗 Fixing internal links for offline navigation...")
        
        # Step 1: Create a mapping of original URLs to their new file paths.
        url_to_filepath = {}
        for page in cloned_pages:
            path = urlparse(page.url.split('?')[0].split('#')[0]).path
            
            file_path = path.strip('/')
            if not file_path or path == '/':
                file_path = 'index.html'
            elif path.endswith('/'):
                file_path = os.path.join(file_path, 'index.html')
            elif not os.path.splitext(file_path)[1]:
                file_path = f'{file_path}.html'
                
            url_to_filepath[page.url] = file_path
            # Also map URL without trailing slash to handle inconsistencies
            if page.url.endswith('/'):
                url_to_filepath[page.url.rstrip('/')] = file_path

        # Step 2: Iterate over each page and rewrite its internal links.
        for page in cloned_pages:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page.html, 'html.parser')
                
                # The directory of the current page, for calculating relative paths.
                current_filepath = url_to_filepath.get(page.url, '')
                current_dir = os.path.dirname(current_filepath)

                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    if not href or href.startswith(('#', 'mailto:', 'tel:')):
                        continue
                    
                    # Resolve the link's URL against the current page's URL.
                    full_url = urljoin(page.url, href)
                    clean_url = full_url.split('?')[0].split('#')[0]
                    
                    # Check if this resolved URL points to a page we have cloned.
                    target_filepath = url_to_filepath.get(clean_url)
                    if not target_filepath and clean_url.endswith('/'):
                        target_filepath = url_to_filepath.get(clean_url.rstrip('/'))

                    if target_filepath:
                        # It's an internal link to a cloned page.
                        # Calculate the relative path from the current page to the target.
                        relative_path = os.path.relpath(target_filepath, start=current_dir)
                        link['href'] = relative_path
                
                page.html = str(soup)
            except Exception as e:
                self.logger.log(f"   ⚠️ Link fixing failed for {page.url}: {str(e)}")
                
        self.logger.log("✅ Internal links fixed")
    
    async def _old_fix_internal_links(self, cloned_pages: List[PageCloneResult], base_url: str):
        """Fix internal links to work within the cloned site"""
        
        await self.logger.log("🔗 Fixing internal links...")
        
        # Create mapping of original URLs to local paths
        url_mapping = {}
        for page in cloned_pages:
            url_mapping[page.url] = page.path
        
        # Fix links in each page
        for page in cloned_pages:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page.html, 'html.parser')
                
                # Fix anchor links
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    
                    # Convert absolute internal links to relative
                    if href.startswith(base_url):
                        if href in url_mapping:
                            link['href'] = url_mapping[href]
                        else:
                            # Strip base URL to make relative
                            link['href'] = href.replace(base_url, '')
                
                # Fix form actions
                forms = soup.find_all('form', action=True)
                for form in forms:
                    action = form['action']
                    if action.startswith(base_url):
                        if action in url_mapping:
                            form['action'] = url_mapping[action]
                        else:
                            form['action'] = action.replace(base_url, '')
                
                # Update page HTML
                page.html = str(soup)
                
            except Exception as e:
                await self.logger.log(f"   ⚠️ Link fixing failed for {page.url}: {str(e)}")
        
        await self.logger.log("✅ Internal links fixed") 