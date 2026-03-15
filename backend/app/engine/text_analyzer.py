"""
LLM-based text analysis for OASIS bridge content.

Extracts structured signals (sentiment, persuasiveness, topic relevance,
novelty) from social media text to inform mathematical dynamics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextSignals:
    """Structured analysis results from a piece of text content."""
    sentiment: float = 0.0          # -1.0 (very negative) to 1.0 (very positive)
    persuasiveness: float = 0.5     # 0.0 (unconvincing) to 1.0 (very persuasive)
    novelty: float = 0.5            # 0.0 (rehash) to 1.0 (completely new angle)
    topic_relevance: dict[str, float] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)


# Fixed fallback for when LLM is unavailable
FALLBACK_SIGNALS = TextSignals()


class TextAnalyzer:
    """Extracts structured signals from text using LLM analysis.

    Falls back to neutral defaults when the LLM is unavailable or fails.
    Uses an LRU-style cache to avoid repeated calls for the same content.
    """

    def __init__(
        self,
        llm_client: Any = None,
        enabled: bool = True,
        cache_size: int = 256,
    ) -> None:
        self._client = llm_client
        self._enabled = enabled
        self._cache: dict[str, TextSignals] = {}
        self._cache_size = cache_size

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    def analyze(
        self,
        content: str,
        context_labels: list[str] | None = None,
    ) -> TextSignals:
        """Analyze text content and return structured signals.

        Args:
            content: The text to analyze (post body, comment, quote).
            context_labels: Labels of existing Idea nodes in the graph,
                           used to assess topic_relevance.

        Returns:
            TextSignals with extracted metrics. Returns FALLBACK_SIGNALS
            on any failure.
        """
        if not self.enabled or not content or not content.strip():
            return FALLBACK_SIGNALS

        # Check cache (truncated key)
        cache_key = content[:200]
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            signals = self._call_llm(content, context_labels or [])
            # Evict oldest if cache full
            if len(self._cache) >= self._cache_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = signals
            return signals
        except Exception:
            logger.warning("TextAnalyzer LLM call failed, using fallback",
                           exc_info=True)
            return FALLBACK_SIGNALS

    def _call_llm(
        self,
        content: str,
        context_labels: list[str],
    ) -> TextSignals:
        """Make the actual LLM call and parse results."""
        labels_str = ", ".join(context_labels[:20]) if context_labels else "none"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a content analysis engine. Analyze the following "
                    "social media text and return a JSON object with these fields:\n"
                    "- sentiment: float from -1.0 (very negative) to 1.0 (very positive)\n"
                    "- persuasiveness: float from 0.0 (unconvincing) to 1.0 (very persuasive)\n"
                    "- novelty: float from 0.0 (complete rehash) to 1.0 (entirely new angle)\n"
                    "- topics: list of 1-3 short topic tags\n"
                    "- topic_relevance: object mapping relevant existing topic labels "
                    "to relevance scores (0.0-1.0). Only include topics with relevance > 0.3.\n\n"
                    f"Existing topic labels: [{labels_str}]"
                ),
            },
            {
                "role": "user",
                "content": content[:500],
            },
        ]

        result = self._client.chat_json(
            messages=messages,
            temperature=0.1,
            max_tokens=300,
        )

        return TextSignals(
            sentiment=max(-1.0, min(1.0, float(result.get("sentiment", 0.0)))),
            persuasiveness=max(0.0, min(1.0, float(result.get("persuasiveness", 0.5)))),
            novelty=max(0.0, min(1.0, float(result.get("novelty", 0.5)))),
            topics=list(result.get("topics", []))[:5],
            topic_relevance={
                str(k): max(0.0, min(1.0, float(v)))
                for k, v in result.get("topic_relevance", {}).items()
            },
        )
