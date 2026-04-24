"""LLM client abstraction with OpenAI and deterministic mock backends."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
import urllib.error
import urllib.request

from project.core.models import SystemState


@dataclass(slots=True)
class LLMClientConfig:
    """Runtime configuration for LLM completion requests."""

    provider: str = "auto"  # auto | openai | mock
    model: str = "gpt-5.4-mini"
    temperature: float = 0.2
    max_tokens: int = 300
    timeout_seconds: int = 12
    api_base_url: str = "https://api.openai.com"
    api_key_env: str = "OPENAI_API_KEY"


class LLMClient:
    """Provide a uniform completion API for agent-side LLM usage."""

    def __init__(self, config: LLMClientConfig) -> None:
        self.config = config

    def complete(
        self,
        prompt: str,
        state: SystemState,
        node_ids: list[str],
    ) -> tuple[str, str]:
        """Return model output text and provider source label."""
        provider = self.config.provider.strip().lower()
        api_key = os.environ.get(self.config.api_key_env, "").strip()

        if provider == "mock":
            return self._mock_response(state, node_ids), "mock"

        if provider in {"openai", "auto"} and api_key:
            try:
                text = self._call_openai(prompt, api_key)
                return text, "openai"
            except Exception:
                if provider == "openai":
                    raise

        return self._mock_response(state, node_ids), "mock"

    def _call_openai(self, prompt: str, api_key: str) -> str:
        """Call OpenAI Responses API with fallback to chat completions endpoint."""
        base = self.config.api_base_url.rstrip("/")
        responses_url = f"{base}/v1/responses"
        payload = {
            "model": self.config.model,
            "input": prompt,
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_tokens,
        }
        try:
            data = self._post_json(responses_url, payload, api_key)
            text = self._extract_responses_text(data)
            if text:
                return text
        except urllib.error.HTTPError as exc:
            if exc.code not in {404, 405}:
                raise

        # Fallback endpoint for compatibility.
        chat_url = f"{base}/v1/chat/completions"
        chat_payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        chat_data = self._post_json(chat_url, chat_payload, api_key)
        return self._extract_chat_text(chat_data)

    def _post_json(self, url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        """Send authenticated JSON POST request and return parsed object payload."""
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            content = response.read().decode("utf-8")
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
        return {}

    def _extract_responses_text(self, data: dict[str, Any]) -> str:
        """Extract assistant text from Responses API schema variants."""
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = data.get("output")
        if not isinstance(output, list):
            return ""
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks).strip()

    def _extract_chat_text(self, data: dict[str, Any]) -> str:
        """Extract assistant text from chat completions payload."""
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content
        return ""

    def _mock_response(self, state: SystemState, node_ids: list[str]) -> str:
        """Produce deterministic JSON decision for reproducible experiments."""
        queue_size = float(state.queue_lengths.get("global", 0))
        high_pressure = queue_size >= 2.0 or state.avg_load >= 0.70
        algorithm_hint = "round-robin" if high_pressure else "min-load"
        if state.intelligence_enabled and state.predicted_queue > queue_size + 0.5:
            algorithm_hint = "round-robin"

        avg_load = state.avg_load if state.node_loads else 0.0
        bias: dict[str, float] = {}
        for node_id in node_ids:
            load = float(state.node_loads.get(node_id, avg_load))
            value = (avg_load - load) * 0.8
            bias[node_id] = max(-0.5, min(0.5, value))

        payload = {
            "algorithm_hint": algorithm_hint,
            "node_bias": bias,
            "confidence": 0.55 if high_pressure else 0.45,
            "reason": "Mock policy: spread load when predicted pressure is high.",
        }
        return json.dumps(payload, ensure_ascii=True)
