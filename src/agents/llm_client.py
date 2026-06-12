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
class SiliconFlowClient:
    """Minimal SiliconFlow chat completions client."""

    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    thinking_budget: int

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
            raise LLMClientError(f"SiliconFlow response parse failed: {body}") from exc

    def create_text_completion(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request and return plain text content."""
        body = self._request(messages=messages)
        try:
            payload = json.loads(body)
            content = payload["choices"][0]["message"]["content"]
            return str(content).strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"SiliconFlow text parse failed: {body}") from exc

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
            "thinking_budget": (
                thinking_budget if thinking_budget is not None else self.thinking_budget
            ),
        }
        if response_format is not None:
            payload["response_format"] = response_format

        request = urllib.request.Request(
            self.base_url,
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
            raise LLMClientError(f"SiliconFlow HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"SiliconFlow connection failed: {exc}") from exc
        except TimeoutError as exc:
            raise LLMClientError("SiliconFlow request timed out") from exc
        except socket.timeout as exc:
            raise LLMClientError("SiliconFlow socket timed out") from exc

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
            raise LLMClientError(f"SiliconFlow response parse failed: {body}") from exc


def build_siliconflow_client(ai_config: dict[str, object]) -> SiliconFlowClient | None:
    """Build a SiliconFlow client from config if an API key is available."""
    if str(ai_config.get("provider", "")).lower() != "siliconflow":
        return None

    api_key_env = str(ai_config.get("api_key_env", "SILICONFLOW_API_KEY"))
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        return None

    return SiliconFlowClient(
        base_url=str(ai_config["base_url"]),
        api_key=api_key,
        model=str(ai_config["model"]),
        temperature=float(ai_config.get("temperature", 0.4)),
        max_tokens=int(ai_config.get("max_tokens", 300)),
        timeout_seconds=int(ai_config.get("request_timeout_seconds", 30)),
        thinking_budget=int(ai_config.get("thinking_budget", 128)),
    )
