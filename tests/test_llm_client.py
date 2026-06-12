import os
import unittest
from unittest.mock import patch

from src.agents.llm_client import OpenAICompatibleClient, build_llm_client
from src.config.defaults import DEFAULT_AI_CONFIG


class LLMClientTests(unittest.TestCase):
    def test_build_llm_client_uses_deepseek_defaults(self) -> None:
        cfg = DEFAULT_AI_CONFIG.copy()
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            client = build_llm_client(cfg)

        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "deepseek")
        self.assertEqual(client.base_url, "https://api.deepseek.com")
        self.assertEqual(client._chat_completions_url(), "https://api.deepseek.com/chat/completions")

    def test_deepseek_payload_uses_thinking_object_not_siliconflow_budget(self) -> None:
        client = OpenAICompatibleClient(
            provider="deepseek",
            base_url="https://api.deepseek.com",
            api_key="test-key",
            model="deepseek-v4-pro",
            temperature=0.4,
            max_tokens=120,
            timeout_seconds=10,
            thinking_budget=8,
            thinking_mode="disabled",
        )
        payload = {}

        client._add_provider_options(payload, thinking_budget=8)

        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertNotIn("thinking_budget", payload)

    def test_siliconflow_payload_keeps_thinking_budget(self) -> None:
        client = OpenAICompatibleClient(
            provider="siliconflow",
            base_url="https://api.siliconflow.cn/v1/chat/completions",
            api_key="test-key",
            model="deepseek-ai/DeepSeek-V4-Pro",
            temperature=0.4,
            max_tokens=120,
            timeout_seconds=10,
            thinking_budget=8,
        )
        payload = {}

        client._add_provider_options(payload, thinking_budget=4)

        self.assertEqual(payload["thinking_budget"], 4)
        self.assertNotIn("thinking", payload)


if __name__ == "__main__":
    unittest.main()
