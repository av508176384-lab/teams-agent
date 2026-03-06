from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    id: str
    chat_id: str
    sender_email: str
    sender_name: str
    body: str
    created: datetime
    is_from_me: bool = False


@dataclass
class Conversation:
    chat_id: str
    topic: str | None
    messages: list[Message] = field(default_factory=list)


@dataclass
class AIResponse:
    reply_text: str
    severity: int  # 1-10
    summary: str  # brief summary for telegram notification
