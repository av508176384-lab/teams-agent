from __future__ import annotations

import json
import logging

from openai import OpenAI

from teams_agent.config import get_env
from teams_agent.models import AIResponse, Message

logger = logging.getLogger(__name__)

SEVERITY_PROMPT = """
You will also assess the conversation severity on a scale of 1-10:
1-3: Normal, friendly conversation
4-6: Slightly tense or complex topics
7-8: Difficult conversation, frustration detected
9-10: Escalation, anger, or urgent issue requiring human attention

Respond ONLY with valid JSON in this exact format:
{"reply": "your reply text here", "severity": 5, "summary": "brief 1-sentence summary of the conversation state"}
"""


class AIResponder:
    def __init__(self, model: str, system_prompt: str) -> None:
        self._client = OpenAI(api_key=get_env("OPENAI_API_KEY"))
        self._model = model
        self._system_prompt = system_prompt

    def generate_response(self, messages: list[Message]) -> AIResponse:
        conversation = []
        for m in messages:
            role = "assistant" if m.is_from_me else "user"
            conversation.append({"role": role, "content": f"[{m.sender_name}]: {m.body}"})

        full_system = f"{self._system_prompt}\n\n{SEVERITY_PROMPT}"

        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": full_system},
                *conversation,
            ],
            temperature=0.7,
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON: %s", raw)
            return AIResponse(reply_text=raw, severity=1, summary="Parse error")

        return AIResponse(
            reply_text=data.get("reply", raw),
            severity=int(data.get("severity", 1)),
            summary=data.get("summary", ""),
        )
