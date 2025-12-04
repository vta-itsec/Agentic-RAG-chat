"""
LLM Service

Unified interface for multiple LLM providers with routing and caching
"""
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional

import yaml
from openai import AsyncOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM provider routing and management"""
    
    def __init__(self):
        self.providers_config = self._load_providers_config()
    
    def _load_providers_config(self) -> List[Dict]:
        """Load providers configuration from yaml"""
        try:
            with open("providers.yaml", "r") as f:
                config = yaml.safe_load(f)
            return config.get("providers", [])
        except FileNotFoundError:
            # Default config if file not found
            return [{
                "name": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key_env": "DEEPSEEK_API_KEY",
                "models": ["deepseek-chat", "deepseek-reasoner"]
            }]
    
    def _get_provider_for_model(self, model_name: str) -> Dict:
        """Get provider config for a specific model"""
        for provider in self.providers_config:
            if model_name in provider.get("models", []):
                return provider
        
        # Default to first provider
        return self.providers_config[0] if self.providers_config else None
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Create chat completion with streaming support
        
        Args:
            model: Model name
            messages: Chat messages
            temperature: Sampling temperature
            tools: Optional function calling tools
            stream: Enable streaming
            
        Yields:
            Server-sent events in OpenAI format
        """
        provider = self._get_provider_for_model(model)
        if not provider:
            raise ValueError(f"No provider found for model: {model}")
        
        # Get API key from environment
        api_key_env = provider["api_key_env"]
        api_key = getattr(settings, api_key_env, None)
        
        if not api_key:
            raise ValueError(f"API key not found for provider: {provider['name']}")
        
        logger.info(f"Using provider: {provider['name']}, model: {model}")
        
        # Create OpenAI client
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=provider["base_url"],
        )
        
        # Prepare request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        # Add built-in tools if none provided
        if tools is None:
            tools = self._get_builtin_tools()
        
        if tools:
            params["tools"] = tools
            logger.info(f"Added {len(tools)} tools to request")
        
        # Call API and stream response
        response = await client.chat.completions.create(**params)
        
        async for chunk in response:
            # Stream content
            if chunk.choices[0].delta.content:
                data = {
                    "id": str(chunk.id),
                    "object": "chat.completion.chunk",
                    "created": chunk.created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk.choices[0].delta.content},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            # Stream tool calls
            elif chunk.choices[0].delta.tool_calls:
                tool_call = chunk.choices[0].delta.tool_calls[0]
                data = {
                    "id": str(chunk.id),
                    "object": "chat.completion.chunk",
                    "created": chunk.created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"tool_calls": [tool_call.dict()]},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
        
        yield "data: [DONE]\n\n"
    
    def _get_builtin_tools(self) -> List[Dict]:
        """Get built-in function calling tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_internal_documents",
                    "description": (
                        "Search for information in the internal company knowledge base. "
                        "Use this when asked about company documents, employees, policies, "
                        "or any uploaded files."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant information"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
