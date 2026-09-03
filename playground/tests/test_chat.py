from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import (  # noqa: E402
    assistant_for_api,
    assistant_from_api,
    llm_payload,
    reasoning_text,
    uses_deepseek,
)


class TestDeepSeekChat(unittest.TestCase):
    def test_detects_deepseek(self) -> None:
        self.assertTrue(uses_deepseek("https://api.deepseek.com", "deepseek-chat"))
        self.assertTrue(uses_deepseek("https://example.com/v1", "deepseek-v4-pro"))
        self.assertFalse(uses_deepseek("https://api.openai.com", "gpt-4o"))

    def test_reasoning_from_official_field(self) -> None:
        self.assertEqual(
            reasoning_text({"reasoning_content": "plan first", "content": "hi"}),
            "plan first",
        )
        self.assertEqual(reasoning_text({"reasoning": {"content": "hidden"}}), "hidden")

    def test_trace_keeps_reasoning_off_content(self) -> None:
        packed = assistant_from_api(
            {
                "content": "这张图认什么？",
                "reasoning_content": "User asked 机甲少女. Lock the anchor.",
                "tool_calls": [],
            }
        )
        self.assertEqual(packed["content"], "这张图认什么？")
        self.assertIn("机甲少女", packed["reasoning_content"])

    def test_replay_reasoning_only_when_asked(self) -> None:
        item = {
            "content": "ok",
            "reasoning_content": "secret cot",
            "tool_calls": [{"id": "1", "function": {"name": "run_skill_script"}}],
        }
        with_cot = assistant_for_api(item, include_reasoning=True)
        without = assistant_for_api(item, include_reasoning=False)
        self.assertEqual(with_cot["reasoning_content"], "secret cot")
        self.assertNotIn("reasoning_content", without)
        self.assertIn("tool_calls", without)

    def test_deepseek_payload_enables_thinking(self) -> None:
        payload = llm_payload(
            "deepseek-chat",
            [{"role": "user", "content": "hi"}],
            tools=[{"type": "function"}],
            base="https://api.deepseek.com",
        )
        self.assertEqual(payload["thinking"], {"type": "enabled"})
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertNotIn("temperature", payload)
        self.assertIn("tools", payload)

    def test_openai_payload_keeps_temperature(self) -> None:
        payload = llm_payload(
            "gpt-4o",
            [{"role": "user", "content": "hi"}],
            tools=None,
            base="https://api.openai.com/v1",
        )
        self.assertEqual(payload["temperature"], 0.2)
        self.assertNotIn("thinking", payload)


if __name__ == "__main__":
    unittest.main()
