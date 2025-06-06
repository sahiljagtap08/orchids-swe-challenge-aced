import time
import asyncio
from typing import Dict, Any, Optional
from ..models.clone import ScrapeResult, LLMCloneResult
from ..core.config import settings
from .llm_clients import LLMClientFactory, create_website_clone_prompt
from .vision_cloner import VisionCloner
from ..core.logging import LiveLogger


class LLMService:
    """LLM service for website cloning with real agentic architecture and vision cloning"""
    
    def __init__(self):
        self.model_configs = settings.ai_model_configs
        self.vision_cloner = VisionCloner()
    
    async def clone_website(
        self, 
        scrape_data: ScrapeResult, 
        model: str = "agentic",
        logger: Optional[LiveLogger] = None
    ) -> LLMCloneResult:
        """
        Clone a website using advanced AI with vision analysis for 100% accuracy
        
        Args:
            scrape_data: The scraped website data
            model: The model configuration to use
            logger: Live logger for real-time updates
            
        Returns:
            LLMCloneResult containing the generated HTML, CSS, and reasoning
        """
        start_time = time.time()
        
        # Use a dummy logger if none is provided
        if not logger:
            class DummyLogger:
                async def log(self, message: str):
                    print(message)
            logger = DummyLogger()

        try:
            if model not in self.model_configs:
                raise ValueError(f"Unknown model configuration: {model}")
            
            config = self.model_configs[model]
            
            # Check if we have a screenshot for vision-enhanced cloning
            has_screenshot = scrape_data.screenshot and len(scrape_data.screenshot) > 100
            
            result: LLMCloneResult

            if has_screenshot and model in ["agentic", "precise"]:
                await logger.log(f"🎨 Using VISION-ENHANCED cloning with screenshot analysis")
                result = await self._vision_enhanced_clone(scrape_data, config, logger)
            elif model == "agentic":
                await logger.log(f"🧠 Using AGENTIC multi-step cloning")
                agentic_result = await self._agentic_clone(scrape_data, config, logger)
                result = LLMCloneResult(
                    html=agentic_result["html"],
                    css=agentic_result.get("css", ""),
                    reasoning=agentic_result.get("reasoning", ""),
                    model_used=f"{config['provider']}/{config['model']}",
                    processing_time=0, # This will be set below
                    screenshot=scrape_data.screenshot # Pass through the original screenshot
                )
            else:
                await logger.log(f"⚡ Using SINGLE-SHOT cloning")
                single_shot_result = await self._single_shot_clone(scrape_data, config, logger)
                result = LLMCloneResult(
                    html=single_shot_result["html"],
                    css=single_shot_result.get("css", ""),
                    reasoning=single_shot_result.get("reasoning", ""),
                    model_used=f"{config['provider']}/{config['model']}",
                    processing_time=0, # This will be set below
                    screenshot=scrape_data.screenshot # Pass through the original screenshot
                )

            
            result.processing_time = time.time() - start_time
            return result
            
        except Exception as e:
            await logger.log(f"❌ LLM processing failed: {str(e)}")
            raise Exception(f"LLM processing failed: {str(e)}")
    
    async def _vision_enhanced_clone(self, scrape_data: ScrapeResult, config: Dict[str, Any], logger: LiveLogger) -> LLMCloneResult:
        """
        Vision-enhanced cloning using screenshot analysis for maximum accuracy
        """
        try:
            await logger.log(f"🎨 Starting vision-enhanced cloning with screenshot analysis")
            
            # Use vision cloner for screenshot analysis
            # This now returns a full LLMCloneResult object
            vision_result = await self.vision_cloner.clone_from_screenshot(
                scrape_result=scrape_data,
                logger=logger
            )
            
            return vision_result
            
        except Exception as e:
            await logger.log(f"⚠️ Vision cloning failed: {str(e)}, falling back to agentic")
            # Fallback returns a dictionary, convert it to LLMCloneResult
            agentic_result = await self._agentic_clone(scrape_data, config, logger)
            return LLMCloneResult(
                html=agentic_result["html"],
                css=agentic_result.get("css", ""),
                reasoning=agentic_result.get("reasoning", "Vision fallback: " + agentic_result.get("reasoning", "")),
                model_used=f"{config['provider']}/{config['model']}",
                processing_time=0,
                screenshot=scrape_data.screenshot
            )
    
    async def _agentic_clone(self, scrape_data: ScrapeResult, config: Dict[str, Any], logger: LiveLogger) -> Dict[str, Any]:
        """
        Multi-agent cloning with reasoning chain using real APIs
        """
        
        provider = config["provider"]
        model_name = config["model"]
        max_tokens = config["max_tokens"]
        
        client = LLMClientFactory.get_client(provider)
        
        reasoning_steps = []
        
        # Agent 1: Layout Analysis
        await logger.log("   - Agent 1: Analyzing layout structure...")
        layout_prompt = create_website_clone_prompt(scrape_data, "layout_analysis")
        layout_analysis = await client.generate_response(
            messages=layout_prompt,
            model=model_name,
            max_tokens=1000
        )
        reasoning_steps.append(f"🏗️ Layout Analysis:\n{layout_analysis}\n")
        await logger.log("   - Agent 1: Layout analysis complete.")
        
        # Small delay between calls to be respectful to APIs
        await asyncio.sleep(0.5)
        
        # Agent 2: Style Extraction
        await logger.log("   - Agent 2: Extracting design and style...")
        style_prompt = create_website_clone_prompt(scrape_data, "style_extraction")
        style_analysis = await client.generate_response(
            messages=style_prompt,
            model=model_name,
            max_tokens=1000
        )
        reasoning_steps.append(f"🎨 Style Analysis:\n{style_analysis}\n")
        await logger.log("   - Agent 2: Style extraction complete.")
        
        await asyncio.sleep(0.5)
        
        # Agent 3: HTML Generation with context from previous agents
        await logger.log("   - Agent 3: Generating final HTML clone...")
        enhanced_prompt = create_website_clone_prompt(scrape_data, "full")
        
        # Add context from previous agents
        context_message = f"""
Previous Analysis Context:

Layout Analysis:
{layout_analysis}

Style Analysis: 
{style_analysis}

Now create the complete HTML clone incorporating these insights:
"""
        
        enhanced_prompt.append({
            "role": "user", 
            "content": context_message
        })
        
        html_result = ""
        async for chunk in client.generate_streaming_response(
            messages=enhanced_prompt,
            model=model_name,
            max_tokens=max_tokens
        ):
            html_result += chunk
            await logger.log(chunk, type='code') # Stream live code to logs
        
        await logger.log("\n   - Agent 3: HTML generation complete.")
        reasoning_steps.append(f"🔨 HTML Generation:\nGenerated complete HTML with {len(html_result)} characters")
        
        # Clean HTML output (remove any markdown formatting)
        html_cleaned = self._clean_html_output(html_result)
        
        reasoning = f"""
🧠 Agentic Cloning Process (Real AI):

{chr(10).join(reasoning_steps)}

✨ Final Result:
- Provider: {provider}
- Model: {model_name}
- Generated {len(html_cleaned)} characters of HTML
- Incorporated layout and style analysis
- Used chain-of-thought reasoning
        """.strip()
        
        return {
            "html": html_cleaned,
            "css": "",  # CSS is inline in HTML
            "reasoning": reasoning
        }
    
    async def _single_shot_clone(self, scrape_data: ScrapeResult, config: Dict[str, Any], logger: LiveLogger) -> Dict[str, Any]:
        """Single-shot cloning for non-agentic models"""
        
        provider = config["provider"]
        model_name = config["model"]
        max_tokens = config["max_tokens"]
        
        client = LLMClientFactory.get_client(provider)
        
        # Create optimized prompt for single-shot generation
        prompt = create_website_clone_prompt(scrape_data, "full")
        
        html_result = ""
        async for chunk in client.generate_streaming_response(
            messages=prompt,
            model=model_name,
            max_tokens=max_tokens
        ):
            html_result += chunk
            await logger.log(chunk, type='code') # Stream live code to logs
        
        html_cleaned = self._clean_html_output(html_result)
        
        reasoning = f"""
⚡ Single-Shot Cloning:
- Provider: {provider}
- Model: {model_name}
- Generated {len(html_cleaned)} characters of HTML
- Direct optimization approach
        """.strip()
        
        return {
            "html": html_cleaned,
            "css": "",
            "reasoning": reasoning
        }
    
    def _clean_html_output(self, html_content: str) -> str:
        """Clean and validate HTML output from LLM"""
        
        # Remove markdown code blocks if present
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        
        # Ensure we have a complete HTML document
        html_content = html_content.strip()
        
        if not html_content.startswith("<!DOCTYPE html>") and not html_content.startswith("<html"):
            # If it's just a fragment, wrap it in a basic HTML structure
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Generated Clone</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        return html_content 