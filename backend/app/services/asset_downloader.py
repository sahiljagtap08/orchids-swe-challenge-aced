import asyncio
import base64
import mimetypes
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import re


class AssetDownloader:
    """Downloads and embeds all external assets for complete offline clones"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self.downloaded_assets: Dict[str, str] = {}  # URL -> base64 content
        self.asset_cache: Dict[str, bytes] = {}     # URL -> raw bytes
        self.processed_urls: Set[str] = set()
        
    async def download_and_embed_assets(self, html: str, base_url: str) -> str:
        """
        Download all external assets and embed them inline for offline use
        
        Args:
            html: Original HTML content
            base_url: Base URL for resolving relative paths
            
        Returns:
            HTML with all assets embedded inline
        """
        
        print(f"📦 Starting comprehensive asset download for {base_url}")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Download all asset types
        await self._download_stylesheets(soup, base_url)
        await self._download_images(soup, base_url)
        await self._download_scripts(soup, base_url)
        await self._download_fonts(soup, base_url)
        
        # Embed assets into HTML
        self._embed_stylesheets(soup)
        self._embed_images(soup)
        self._embed_scripts(soup)
        
        print(f"✅ Asset embedding complete: {len(self.downloaded_assets)} assets processed")
        
        return str(soup)
    
    async def _download_stylesheets(self, soup: BeautifulSoup, base_url: str):
        """Download and process CSS files"""
        
        print("🎨 Downloading stylesheets...")
        
        css_links = soup.find_all('link', {'rel': 'stylesheet'})
        
        for link in css_links:
            href = link.get('href')
            if href:
                css_url = urljoin(base_url, href)
                
                if css_url not in self.processed_urls:
                    css_content = await self._download_asset(css_url, 'text/css')
                    if css_content:
                        # Process CSS to download referenced assets
                        processed_css = await self._process_css_assets(css_content, css_url)
                        self.downloaded_assets[css_url] = processed_css
                        self.processed_urls.add(css_url)
    
    async def _download_images(self, soup: BeautifulSoup, base_url: str):
        """Download all images"""
        
        print("🖼️ Downloading images...")
        
        # Regular img tags
        images = soup.find_all('img')
        for img in images:
            src = img.get('src')
            if src:
                img_url = urljoin(base_url, src)
                await self._download_and_cache_binary_asset(img_url)
        
        # Background images in inline styles
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')
            bg_urls = re.findall(r'background-image:\s*url\(["\']?([^"\')\s]+)["\']?\)', style)
            for bg_url in bg_urls:
                full_url = urljoin(base_url, bg_url)
                await self._download_and_cache_binary_asset(full_url)
    
    async def _download_scripts(self, soup: BeautifulSoup, base_url: str):
        """Download JavaScript files"""
        
        print("⚙️ Downloading scripts...")
        
        scripts = soup.find_all('script', src=True)
        
        for script in scripts:
            src = script.get('src')
            if src:
                script_url = urljoin(base_url, src)
                
                if script_url not in self.processed_urls:
                    js_content = await self._download_asset(script_url, 'application/javascript')
                    if js_content:
                        self.downloaded_assets[script_url] = js_content
                        self.processed_urls.add(script_url)
    
    async def _download_fonts(self, soup: BeautifulSoup, base_url: str):
        """Download font files from CSS and link tags"""
        
        print("🔤 Downloading fonts...")
        
        # Font links (Google Fonts, etc.)
        font_links = soup.find_all('link', href=True)
        
        for link in font_links:
            href = link.get('href', '')
            if 'font' in href.lower() or 'googleapis.com/css' in href:
                font_css_url = urljoin(base_url, href)
                
                if font_css_url not in self.processed_urls:
                    font_css = await self._download_asset(font_css_url, 'text/css')
                    if font_css:
                        # Download actual font files referenced in CSS
                        processed_font_css = await self._process_css_assets(font_css, font_css_url)
                        self.downloaded_assets[font_css_url] = processed_font_css
                        self.processed_urls.add(font_css_url)
    
    async def _process_css_assets(self, css_content: str, css_base_url: str) -> str:
        """Process CSS and download referenced assets (fonts, images)"""
        
        # Find all url() references in CSS
        url_pattern = r'url\(["\']?([^"\')\s]+)["\']?\)'
        urls = re.findall(url_pattern, css_content)
        
        for url in urls:
            full_url = urljoin(css_base_url, url)
            
            # Download the asset
            await self._download_and_cache_binary_asset(full_url)
            
            # Replace URL in CSS with data URI
            if full_url in self.asset_cache:
                data_uri = self._create_data_uri(full_url, self.asset_cache[full_url])
                css_content = css_content.replace(url, data_uri)
        
        return css_content
    
    async def _download_asset(self, url: str, content_type: str) -> Optional[str]:
        """Download a text asset (CSS, JS)"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    return response.text
                
        except Exception as e:
            print(f"⚠️ Failed to download {url}: {str(e)}")
        
        return None
    
    async def _download_and_cache_binary_asset(self, url: str):
        """Download and cache binary assets (images, fonts)"""
        
        if url in self.asset_cache:
            return
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    self.asset_cache[url] = response.content
                    print(f"✅ Downloaded asset: {url} ({len(response.content)} bytes)")
                
        except Exception as e:
            print(f"⚠️ Failed to download asset {url}: {str(e)}")
    
    def _create_data_uri(self, url: str, content: bytes) -> str:
        """Create a data URI from binary content"""
        
        # Guess MIME type from URL
        mime_type, _ = mimetypes.guess_type(url)
        if not mime_type:
            # Default MIME types for common assets
            if url.endswith(('.woff', '.woff2')):
                mime_type = 'font/woff2'
            elif url.endswith('.ttf'):
                mime_type = 'font/ttf'
            elif url.endswith('.otf'):
                mime_type = 'font/otf'
            else:
                mime_type = 'application/octet-stream'
        
        # Create base64 data URI
        b64_content = base64.b64encode(content).decode('utf-8')
        return f"data:{mime_type};base64,{b64_content}"
    
    def _embed_stylesheets(self, soup: BeautifulSoup):
        """Replace external CSS links with inline styles"""
        
        css_links = soup.find_all('link', {'rel': 'stylesheet'})
        
        for link in css_links:
            href = link.get('href')
            if href:
                css_url = urljoin(soup.find('base').get('href', ''), href) if soup.find('base') else href
                
                if css_url in self.downloaded_assets:
                    # Create inline style tag
                    style_tag = soup.new_tag('style')
                    style_tag.string = self.downloaded_assets[css_url]
                    
                    # Replace link with style tag
                    link.replace_with(style_tag)
    
    def _embed_images(self, soup: BeautifulSoup):
        """Replace image sources with data URIs"""
        
        images = soup.find_all('img')
        
        for img in images:
            src = img.get('src')
            if src and src in self.asset_cache:
                data_uri = self._create_data_uri(src, self.asset_cache[src])
                img['src'] = data_uri
        
        # Handle background images in inline styles
        elements_with_style = soup.find_all(attrs={"style": True})
        for element in elements_with_style:
            style = element.get('style', '')
            
            # Replace background-image URLs with data URIs
            def replace_bg_url(match):
                url = match.group(1)
                if url in self.asset_cache:
                    data_uri = self._create_data_uri(url, self.asset_cache[url])
                    return f'url({data_uri})'
                return match.group(0)
            
            new_style = re.sub(r'url\(["\']?([^"\')\s]+)["\']?\)', replace_bg_url, style)
            element['style'] = new_style
    
    def _embed_scripts(self, soup: BeautifulSoup):
        """Replace external scripts with inline scripts"""
        
        scripts = soup.find_all('script', src=True)
        
        for script in scripts:
            src = script.get('src')
            if src and src in self.downloaded_assets:
                # Create inline script
                script['src'] = None  # Remove src attribute
                script.string = self.downloaded_assets[src] 