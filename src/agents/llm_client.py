"""LLM client interface."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass


class LLMClientError(RuntimeError):
    """Raised when the external LLM client fails."""


@dataclass(slots=True)
class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat completions client."""

    provider: str
    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    thinking_budget: int
    thinking_mode: str = "disabled"
    reasoning_effort: str = "high"

    def create_json_completion(self, messages: list[dict[str, str]]) -> dict[str, object]:
        """Send a chat completion request and parse a JSON object from the response."""
        body = self._request(
            messages=messages,
            response_format={"type": "json_object"},
        )
        try:
            payload = json.loads(body)
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"{self.provider} response parse failed: {body}") from exc

    def create_text_completion(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request and return plain text content."""
        body = self._request(messages=messages)
        try:
            payload = json.loads(body)
            content = payload["choices"][0]["message"]["content"]
            return str(content).strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"{self.provider} text parse failed: {body}") from exc

    def _request(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, object] | None = None,
        max_tokens: int | None = None,
        thinking_budget: int | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        self._add_provider_options(payload, thinking_budget=thinking_budget)
        if response_format is not None:
            payload["response_format"] = response_format

        request = urllib.request.Request(
            self._chat_completions_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"{self.provider} HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"{self.provider} connection failed: {exc}") from exc
        except TimeoutError as exc:
            raise LLMClientError(f"{self.provider} request timed out") from exc
        except socket.timeout as exc:
            raise LLMClientError(f"{self.provider} socket timed out") from exc

    def _chat_completions_url(self) -> str:
        base_url = self.base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _add_provider_options(
        self,
        payload: dict[str, object],
        *,
        thinking_budget: int | None,
    ) -> None:
        if self.provider == "siliconflow":
            payload["thinking_budget"] = (
                thinking_budget if thinking_budget is not None else self.thinking_budget
            )
            return
        if self.provider == "deepseek":
            mode = self.thinking_mode.strip().lower()
            if mode not in {"enabled", "disabled"}:
                mode = "disabled"
            payload["thinking"] = {"type": mode}
            if mode == "enabled":
                payload["reasoning_effort"] = self.reasoning_effort

    def create_json_completion_with_limits(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        thinking_budget: int,
    ) -> dict[str, object]:
        """Send a JSON completion request with per-call token limits."""
        body = self._request(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )
        try:
            payload = json.loads(body)
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"{self.provider} response parse failed: {body}") from exc


SiliconFlowClient = OpenAICompatibleClient


def build_llm_client(ai_config: dict[str, object]) -> OpenAICompatibleClient | None:
    """Build an OpenAI-compatible client from config if an API key is available."""
    provider = str(ai_config.get("provider", "")).strip().lower()
    if provider not in {"deepseek", "siliconflow"}:
        return None

    default_key_env = "DEEPSEEK_API_KEY" if provider == "deepseek" else "SILICONFLOW_API_KEY"
    api_key_env = str(ai_config.get("api_key_env", default_key_env))
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        return None

    default_base_url = (
        "https://api.deepseek.com"
        if provider == "deepseek"
        else "https://api.siliconflow.cn/v1/chat/completions"
    )
    default_model = "deepseek-v4-pro" if provider == "deepseek" else "deepseek-ai/DeepSeek-V4-Pro"
    return OpenAICompatibleClient(
        provider=provider,
        base_url=str(ai_config.get("base_url", default_base_url)),
        api_key=api_key,
        model=str(ai_config.get("model", default_model)),
        temperature=float(ai_config.get("temperature", 0.4)),
        max_tokens=int(ai_config.get("max_tokens", 300)),
        timeout_seconds=int(ai_config.get("request_timeout_seconds", 30)),
        thinking_budget=int(ai_config.get("thinking_budget", 128)),
        thinking_mode=str(ai_config.get("thinking_mode", "disabled")),
        reasoning_effort=str(ai_config.get("reasoning_effort", "high")),
    )


def build_siliconflow_client(ai_config: dict[str, object]) -> OpenAICompatibleClient | None:
    """Backward-compatible alias for older call sites."""
    return build_llm_client(ai_config)


def llm_source_label(ai_config: dict[str, object], client: object | None = None) -> str:
    """Return a stable source label for audit and CLI output."""
    provider = getattr(client, "provider", None)
    if isinstance(provider, str) and provider:
        return provider
    configured = str(ai_config.get("provider", "")).strip().lower()
    if configured in {"deepseek", "siliconflow"}:
        return configured
    return "siliconflow"
