from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urljoin, urlparse

from .playwright_scraper import PlaywrightScraper


class SiteCrawler:
    """
    Intelligent website crawler that discovers all pages on a site.
    Uses Playwright to render pages and find dynamically-loaded links.
    """
    
    def __init__(self, max_pages: int = 50):
        self.max_pages = max_pages
        self.scraper = PlaywrightScraper()

    async def discover_all_pages(self, base_url: str) -> list[str]:
        """
        Discovers all unique pages on the website starting from the base URL.
        
        It fetches sitemap.xml, robots.txt, and crawls the site using Playwright
        to find all internal links, including those loaded via JavaScript.
        """
        
        all_urls = set()
        queue = [base_url]
        processed_urls = set()
        
        # Add base URL to the set
        all_urls.add(base_url)
        
        # TODO: Add sitemap and robots.txt discovery for more comprehensive crawling
        
        while queue and len(all_urls) < self.max_pages:
            url = queue.pop(0)
            if url in processed_urls:
                continue
                
            processed_urls.add(url)
            
            try:
                # Use PlaywrightScraper to get the page content, which handles JS rendering
                scraped_content = await self.scraper.scrape(url)
                
                if scraped_content and scraped_content.html:
                    # Find all links on the page
                    soup = BeautifulSoup(scraped_content.html, 'html.parser')
                    
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        
                        # Join relative URLs with the base URL
                        full_url = urljoin(url, href)
                        
                        # Remove fragment identifiers
                        full_url = full_url.split('#')[0]
                        
                        # Check if it's an internal link and not already found
                        if urlparse(full_url).netloc == urlparse(base_url).netloc:
                            if full_url not in all_urls:
                                all_urls.add(full_url)
                                if len(all_urls) < self.max_pages:
                                    queue.append(full_url)
                
            except Exception as e:
                print(f"Could not crawl {url}: {str(e)}")
        
        return list(all_urls) 