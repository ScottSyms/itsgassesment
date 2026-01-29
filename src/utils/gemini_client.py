"""Gemini API client wrapper for the ITSG-33 system."""

import os
from typing import Optional, List, Dict, Any

import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class GeminiConfig(BaseModel):
    """Gemini configuration."""

    api_key: str
    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 8192


class GeminiClient:
    """Wrapper for Google Gemini API."""

    def __init__(self, config: Optional[GeminiConfig] = None):
        """Initialize Gemini client."""
        if config is None:
            config = GeminiConfig(
                api_key=os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
            )

        self.config = config
        genai.configure(api_key=config.api_key)

        self.generation_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "max_output_tokens": config.max_output_tokens,
        }

        self.model = genai.GenerativeModel(
            model_name=config.model_name, generation_config=self.generation_config
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from Gemini."""
        response = self.model.generate_content(prompt, **kwargs)
        return response.text

    async def generate_async(self, content: Any, **kwargs) -> str:
        """Async generate response from Gemini."""
        response = await self.model.generate_content_async(content, **kwargs)
        return response.text

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Chat with Gemini using conversation history."""
        chat = self.model.start_chat(history=[])

        for msg in messages[:-1]:
            chat.send_message(msg["content"])

        response = chat.send_message(messages[-1]["content"])
        return response.text

    def analyze_document(self, document_content: str, analysis_prompt: str) -> str:
        """Analyze a document with a specific prompt."""
        full_prompt = f"""
        Document Content:
        {document_content}

        Analysis Request:
        {analysis_prompt}
        """
        return self.generate(full_prompt)

    def extract_controls(self, document_content: str) -> Dict[str, Any]:
        """Extract security controls mentioned in a document."""
        prompt = f"""
        Analyze the following document and identify all ITSG-33 security controls
        mentioned or implied. For each control, provide:
        - Control ID (e.g., AC-1, AU-2)
        - Control Name
        - Relevant excerpt from document
        - Assessment of implementation status (Implemented, Partial, Not Implemented, Unknown)

        Document:
        {document_content}

        Return as JSON format.
        """
        response = self.generate(prompt)
        return {"raw_response": response}
