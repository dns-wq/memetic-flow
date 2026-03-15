"""
LLM client wrapper
Uses Anthropic Claude API (Messages API format)
"""

import json
import re
from typing import Optional, Dict, Any, List

import anthropic

from ..config import Config


class LLMClient:
    """LLM client using Anthropic Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Supports 'system', 'user', and 'assistant' roles.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens in response.
            response_format: Ignored (kept for interface compatibility).

        Returns:
            Model response text.
        """
        # Anthropic Messages API uses a separate `system` parameter.
        # Extract any system messages and merge them.
        system_parts = []
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        # Ensure the conversation starts with a user message (Anthropic requirement).
        # If the first non-system message is an assistant message, prepend a placeholder.
        if api_messages and api_messages[0]["role"] == "assistant":
            api_messages.insert(0, {"role": "user", "content": "Continue."})

        # Merge consecutive same-role messages (Anthropic requires alternating roles).
        merged = []
        for msg in api_messages:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged.append(dict(msg))
        api_messages = merged

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        response = self.client.messages.create(**kwargs)
        content = response.content[0].text
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send a chat request and parse the response as JSON.

        The system prompt is augmented to instruct the model to respond
        with valid JSON only.

        Args:
            messages: List of message dicts.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Parsed JSON object.
        """
        # Inject a JSON instruction into the system prompt so Claude
        # returns well-formed JSON without markdown wrappers.
        json_instruction = {
            "role": "system",
            "content": (
                "You must respond with valid JSON only. "
                "Do not include markdown code fences, explanations, or any other text. "
                "Output raw JSON."
            ),
        }
        augmented_messages = [json_instruction] + list(messages)

        response = self.chat(
            messages=augmented_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Clean any markdown code block wrappers the model may still add
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {cleaned}")
