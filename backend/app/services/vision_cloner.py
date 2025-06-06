import asyncio
import base64
import time
from typing import Optional, Dict, Any, List
import httpx
from PIL import Image
import io

from ..core.config import settings
from ..models.clone import ScrapeResult, LLMCloneResult
from ..core.logging import LiveLogger


class VisionCloner:
    """Screenshot-first cloning using AI vision models for 100% visual accuracy"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(120.0)
    
    async def clone_from_screenshot(
        self, 
        scrape_result: ScrapeResult,
        logger: Optional[LiveLogger] = None
    ) -> LLMCloneResult:
        """
        Clone website using screenshot analysis with vision models
        
        Args:
            scrape_result: The result from the scraper, containing URL, HTML, and screenshot.
            logger: Live logger instance.
            
        Returns:
            LLMCloneResult containing the generated HTML and other metadata.
        """
        
        # Use a dummy logger if none is provided
        if not logger:
            class DummyLogger:
                async def log(self, message: str):
                    print(message)
            logger = DummyLogger()

        try:
            url = scrape_result.url
            screenshot_b64 = scrape_result.screenshot
            html_content = scrape_result.html
            
            if not screenshot_b64:
                raise ValueError("A screenshot is required for vision-based cloning.")

            await logger.log(f"🎨 Using VISION-ENHANCED cloning with screenshot analysis")
            
            start_time = time.time()
            
            # Step 1: Analyze screenshot with GPT-4 Vision
            await logger.log("     - Step 1: Analyzing screenshot with GPT-4 Vision...")
            visual_analysis = await self._analyze_screenshot_with_vision(screenshot_b64, url, logger)
            
            # Step 2: Extract color palette from screenshot
            await logger.log("     - Step 2: Extracting color palette...")
            color_palette = await self._extract_color_palette(screenshot_b64, logger)
            
            # Step 3: Generate HTML based on visual analysis
            await logger.log("     - Step 3: Generating HTML from vision analysis...")
            html_result = await self._generate_html_from_vision(
                visual_analysis, color_palette, url, html_content, logger
            )
            
            processing_time = time.time() - start_time
            await logger.log(f"   - ✅ Vision cloning completed: {len(html_result)} chars in {processing_time:.2f}s")
            
            return LLMCloneResult(
                html=html_result,
                css="", # CSS is embedded in the HTML for this cloner
                reasoning=visual_analysis,
                model_used="gpt-4o", # Hardcoded for now, can be dynamic
                processing_time=processing_time,
                screenshot=screenshot_b64 # IMPORTANT: Return the screenshot
            )
            
        except Exception as e:
            await logger.log(f"   - ❌ Vision cloning failed: {str(e)}")
            raise e
    
    async def _analyze_screenshot_with_vision(self, screenshot_b64: str, url: str, logger: LiveLogger) -> str:
        """Analyze screenshot using GPT-4 Vision for detailed layout description"""
        
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key required for vision analysis")
        
        vision_prompt = f"""
        PIXEL-PERFECT WEBSITE ANALYSIS TASK

        Analyze this website screenshot with EXTREME DETAIL for 100% accurate recreation:

        TARGET URL: {url}

        PROVIDE COMPREHENSIVE VISUAL ANALYSIS:

        1. **LAYOUT STRUCTURE**:
           - Exact header layout, height, and positioning
           - Navigation menu style and alignment
           - Main content area structure and proportions
           - Footer design and placement
           - Grid/column layouts used

        2. **COLOR ANALYSIS**:
           - Background colors (hex codes if possible)
           - Text colors for different elements
           - Button colors and hover states
           - Border and accent colors
           - Gradient patterns or solid colors

        3. **TYPOGRAPHY DETAILS**:
           - Font families and styles used
           - Font sizes for headings (H1, H2, H3)
           - Font weights (bold, normal, light)
           - Text alignment and spacing
           - Line heights and letter spacing

        4. **VISUAL ELEMENTS**:
           - Button styles, borders, and shadows
           - Image placement and sizing
           - Icon styles and positioning
           - Card/container designs
           - Spacing between elements

        5. **SPECIFIC MEASUREMENTS**:
           - Approximate padding and margins
           - Element widths and heights
           - Border radius values
           - Shadow effects and depth

        6. **BRAND IDENTITY**:
           - Visual tone and style
           - Key design patterns
           - Unique visual elements
           - Overall aesthetic approach

        Be extremely specific about colors, sizes, positioning, and styling. This analysis will be used to recreate the design with 100% visual accuracy.
        """

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "max_tokens": 2000,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": vision_prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{screenshot_b64}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis = result["choices"][0]["message"]["content"]
                    await logger.log(f"     - Vision analysis successful ({len(analysis)} chars)")
                    return analysis
                else:
                    await logger.log(f"     - ❌ Vision API failed: {response.status_code}")
                    return "Vision analysis failed"
                    
        except Exception as e:
            await logger.log(f"     - ❌ Vision analysis error: {str(e)}")
            return "Vision analysis error"
    
    async def _extract_color_palette(self, screenshot_b64: str, logger: LiveLogger) -> Dict[str, str]:
        """Extract dominant colors from screenshot"""
        
        try:
            # Decode base64 image
            image_data = base64.b64decode(screenshot_b64)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get dominant colors using simple sampling
            # Sample from different regions to get background, text, accent colors
            width, height = image.size
            
            colors = {}
            
            # Sample background (top-left corner)
            bg_color = image.getpixel((width // 10, height // 10))
            colors["background"] = f"rgb({bg_color[0]}, {bg_color[1]}, {bg_color[2]})"
            
            # Sample header area
            header_color = image.getpixel((width // 2, height // 20))
            colors["header"] = f"rgb({header_color[0]}, {header_color[1]}, {header_color[2]})"
            
            # Sample main content area
            content_color = image.getpixel((width // 2, height // 2))
            colors["content"] = f"rgb({content_color[0]}, {content_color[1]}, {content_color[2]})"
            
            await logger.log(f"     - 🎨 Extracted colors: {colors}")
            return colors
            
        except Exception as e:
            await logger.log(f"     - ❌ Color extraction failed: {str(e)}")
            return {
                "background": "rgb(255, 255, 255)",
                "header": "rgb(248, 249, 250)",
                "content": "rgb(255, 255, 255)"
            }
    
    async def _generate_html_from_vision(
        self, 
        visual_analysis: str, 
        color_palette: Dict[str, str], 
        url: str, 
        html_content: str,
        logger: LiveLogger
    ) -> str:
        """Generate HTML based on vision analysis"""
        
        generation_prompt = f"""
        PIXEL-PERFECT HTML GENERATION FROM VISION ANALYSIS

        Create a 100% visually accurate HTML clone based on this detailed analysis:

        ORIGINAL URL: {url}

        DETAILED VISUAL ANALYSIS:
        {visual_analysis}

        EXTRACTED COLOR PALETTE:
        {color_palette}

        ORIGINAL HTML CONTEXT:
        {html_content[:2000]}...

        CRITICAL REQUIREMENTS:

        1. **EXACT VISUAL RECREATION**:
           - Use the exact colors, fonts, and spacing described in the analysis
           - Match the layout structure pixel-perfectly
           - Recreate all visual elements (buttons, cards, etc.) exactly
           - Maintain the same visual hierarchy and proportions

        2. **COMPLETE HTML DOCUMENT**:
           - Include DOCTYPE, head, and body sections
           - Embed ALL CSS inline for standalone functionality
           - Use modern CSS (Flexbox, Grid, custom properties)
           - Add responsive design for mobile compatibility

        3. **VISUAL FIDELITY FOCUS**:
           - Prioritize visual appearance over functionality
           - Use the extracted colors and visual patterns
           - Include hover effects and transitions
           - Ensure typography matches exactly

        4. **TECHNICAL EXCELLENCE**:
           - Clean, semantic HTML structure
           - Efficient CSS with proper organization
           - Cross-browser compatibility
           - Accessibility considerations

        Generate the complete HTML document that recreates the visual design with 100% accuracy.

        RETURN ONLY THE HTML CODE - NO EXPLANATIONS.
        """

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "max_tokens": 4000,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert web designer focused on creating pixel-perfect visual clones. Generate only clean HTML with embedded CSS."
                            },
                            {
                                "role": "user",
                                "content": generation_prompt
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    html_output = result["choices"][0]["message"]["content"]
                    
                    # Clean the output
                    if html_output.startswith("```html"):
                        html_output = html_output[7:]
                    if html_output.startswith("```"):
                        html_output = html_output[3:]
                    if html_output.endswith("```"):
                        html_output = html_output[:-3]
                    
                    await logger.log(html_output) # Stream live code
                    return html_output.strip()
                else:
                    await logger.log(f"     - ❌ HTML generation failed: {response.status_code}")
                    return "<html><body><h1>Vision cloning failed</h1></body></html>"
                    
        except Exception as e:
            await logger.log(f"     - ❌ HTML generation error: {str(e)}")
            return "<html><body><h1>HTML generation error</h1></body></html>" 