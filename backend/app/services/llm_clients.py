import asyncio
import base64
from typing import Dict, Any, Optional, List, AsyncGenerator
from abc import ABC, abstractmethod

import anthropic
import openai
import google.generativeai as genai
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ..core.config import settings
from ..models.clone import ScrapeResult


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str,
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        yield "" # To make it an async generator


class AnthropicClient(BaseLLMClient):
    """Claude API client"""
    
    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Generate response using Claude"""
        
        try:
            # Convert messages to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=claude_messages,
                system=system_message,
                **kwargs
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Claude."""
        try:
            # Convert messages to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                messages=claude_messages,
                system=system_message,
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise Exception(f"Claude API streaming error: {str(e)}")


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT API client"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gpt-4o",
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Generate response using GPT"""
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gpt-4o",
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from GPT."""
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            raise Exception(f"OpenAI API streaming error: {str(e)}")


class GoogleClient(BaseLLMClient):
    """Google Gemini API client"""
    
    def __init__(self):
        if not settings.google_ai_api_key:
            raise ValueError("GOOGLE_AI_API_KEY not configured")
        
        genai.configure(api_key=settings.google_ai_api_key)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gemini-2.0-flash-exp",
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Generate response using Gemini"""
        
        try:
            # Convert messages to Gemini format
            gemini_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    # Prepend system message to first user message
                    if gemini_messages and gemini_messages[-1]["role"] == "user":
                        gemini_messages[-1]["parts"][0] = f"{msg['content']}\n\n{gemini_messages[-1]['parts'][0]}"
                    else:
                        gemini_messages.append({
                            "role": "user",
                            "parts": [msg["content"]]
                        })
                elif msg["role"] == "user":
                    gemini_messages.append({
                        "role": "user", 
                        "parts": [msg["content"]]
                    })
                elif msg["role"] == "assistant":
                    gemini_messages.append({
                        "role": "model",
                        "parts": [msg["content"]]
                    })
            
            model_instance = genai.GenerativeModel(model)
            
            # Use asyncio to run the sync method
            response = await asyncio.to_thread(
                model_instance.generate_content,
                gemini_messages,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    **kwargs
                )
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Google AI API error: {str(e)}")

    async def generate_streaming_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = "gemini-2.0-flash-exp",
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Gemini."""
        try:
            # Convert messages to Gemini format
            gemini_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    # Prepend system message to first user message
                    if gemini_messages and gemini_messages[-1]["role"] == "user":
                        gemini_messages[-1]["parts"][0] = f"{msg['content']}\n\n{gemini_messages[-1]['parts'][0]}"
                    else:
                        gemini_messages.append({
                            "role": "user",
                            "parts": [msg["content"]]
                        })
                elif msg["role"] == "user":
                    gemini_messages.append({
                        "role": "user", 
                        "parts": [msg["content"]]
                    })
                elif msg["role"] == "assistant":
                    gemini_messages.append({
                        "role": "model",
                        "parts": [msg["content"]]
                    })
            
            model_instance = genai.GenerativeModel(model)
            
            # Use asyncio to run the sync method
            response_stream = await asyncio.to_thread(
                model_instance.generate_content,
                gemini_messages,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    **kwargs
                ),
                stream=True
            )
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            raise Exception(f"Google AI API streaming error: {str(e)}")


class LLMClientFactory:
    """Factory for creating LLM clients"""
    
    _clients: Dict[str, BaseLLMClient] = {}
    
    @classmethod
    def get_client(cls, provider: str) -> BaseLLMClient:
        """Get or create an LLM client for the given provider"""
        
        if provider not in cls._clients:
            if provider == "anthropic":
                cls._clients[provider] = AnthropicClient()
            elif provider == "openai":
                cls._clients[provider] = OpenAIClient()
            elif provider == "google":
                cls._clients[provider] = GoogleClient()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        
        return cls._clients[provider]


def create_website_clone_prompt(scrape_data: ScrapeResult, step: str = "full") -> List[Dict[str, Any]]:
    """
    Creates a structured, multi-step prompt for high-fidelity website cloning.
    """
    
    system_prompt = """
You are an expert-level frontend developer specializing in creating pixel-perfect, responsive, and production-ready website clones from provided materials. Your task is to generate a single, self-contained HTML file with embedded CSS and, if necessary, JavaScript.

**Core Principles:**
1.  **Extreme Fidelity:** Your primary goal is to match the visual and structural details of the provided screenshot and HTML with 100% accuracy.
2.  **Modern Code:** Use modern HTML5 semantics and responsive CSS (Flexbox, Grid). All CSS must be inside a `<style>` tag in the `<head>`.
3.  **Component-Based Approach:** Deconstruct the website into logical components (header, hero, content sections, footer), build them meticulously, and then assemble them.
4.  **No Placeholders (Unless Necessary):** Recreate all content and images as described. Only use placeholder images if the original assets are missing from the context.
5.  **Self-Contained:** The final output must be a single HTML file.
"""

    user_prompt_context = f"""
**Project Context:**
- **URL:** {scrape_data.url}
- **Original HTML Structure:** The following is the original HTML structure of the page. Use this as a guide for content, structure, and semantics.
  ```html
  {scrape_data.html[:8000]}
  ```
- **Original CSS:** The following are some of the original CSS styles. Use these for reference on colors, fonts, and layout, but prioritize the visual accuracy of the screenshot.
  ```css
  {scrape_data.css[:4000] if scrape_data.css else "No CSS provided."}
  ```
- **Screenshot:** You have access to a screenshot of the page for pixel-perfect visual details.
"""

    # Base structure for prompts, preparing for vision models
    # Content is a list to allow for multiple parts (text and image)
    prompts = {
        "layout_analysis": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "content": f"""
{user_prompt_context}

**Your Task (Step 1 - Layout Analysis):**
Based on the provided screenshot, HTML structure, and CSS, analyze and deconstruct the website's layout into a high-level component structure.

**Output Format (JSON):**
Return a JSON object describing the components. For each component, specify its name and a brief description of its content and purpose.

**Example:**
```json
{{
  "components": [
    {{"name": "Header", "description": "Contains the logo and main navigation links."}},
    {{"name": "HeroSection", "description": "Large hero image with a headline and a call-to-action button."}},
    {{"name": "Features", "description": "A three-column grid showcasing product features."}},
    {{"name": "Footer", "description": "Contains contact information and social media links."}}
  ]
}}
```
"""}
            ]}
        ],
        "style_extraction": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "content": f"""
{user_prompt_context}

**Your Task (Step 2 - Style Extraction):**
Based on the provided screenshot, HTML, and CSS, extract the key design and style properties.

**Output Format (JSON):**
Return a JSON object containing the color palette and typography details. Use CSS variables for colors.

**Example:**
```json
{{
  "palette": [
    {{"name": "--primary-color", "value": "#0A66C2"}},
    {{"name": "--text-color", "value": "#333333"}},
    {{"name": "--background-color", "value": "#FFFFFF"}}
  ],
  "typography": {{
    "fontFamily": "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    "baseFontSize": "16px",
    "headings": {{
      "h1": {{"fontSize": "2.5rem", "fontWeight": "600"}},
      "h2": {{"fontSize": "2rem", "fontWeight": "500"}}
    }}
  }}
}}
```
"""}
            ]}
        ],
        "full": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "content": f"""
{user_prompt_context}

**Your Task (Final Step - HTML Generation):**
Generate the complete, self-contained HTML file for the website. Adhere strictly to the context provided.

**Critical Instructions:**
1.  **Use the Component Structure:** Build the page using the logical components you identified (Header, Hero, etc.).
2.  **Embed CSS:** Create a `<style>` tag in the `<head>` and place all CSS there. Use CSS variables for colors as extracted.
3.  **Match Visuals Perfectly:** The final output must be a pixel-perfect match to the screenshot. Pay close attention to spacing, alignment, colors, and fonts.
4.  **Output ONLY Code:** Do not add any commentary, explanations, or markdown formatting around the HTML code. Your entire response should be the HTML document itself, starting with `<!DOCTYPE html>`.
"""}
            ]}
        ]
    }
    
    # Add the screenshot image data to the prompt if it exists
    if scrape_data.screenshot:
        screenshot_message = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{scrape_data.screenshot}",
                "detail": "high"
            }
        }
        
        # Add screenshot to all user prompts
        for key in prompts:
            user_content = prompts[key][1]["content"]
            if isinstance(user_content, list):
                # Append the image part to the content list
                user_content.append(screenshot_message)

    return prompts.get(step, prompts["full"])