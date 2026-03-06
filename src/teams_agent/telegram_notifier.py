from __future__ import annotations

import logging

import httpx

from teams_agent.config import get_env

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier:
    def __init__(self) -> None:
        self._token = get_env("TELEGRAM_BOT_TOKEN")
        self._chat_id = get_env("TELEGRAM_CHAT_ID")
        self._http = httpx.Client(timeout=15)

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_API}/bot{self._token}/{method}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        try:
            resp = self._http.post(
                self._url("sendMessage"),
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.exception("Failed to send Telegram message")
            return False

    def notify_tough_conversation(
        self,
        contact_name: str,
        severity: int,
        summary: str,
    ) -> bool:
        text = (
            f"<b>Teams Alert - Tough Conversation Detected</b>\n\n"
            f"<b>Contact:</b> {contact_name}\n"
            f"<b>Severity:</b> {severity}/10\n"
            f"<b>Summary:</b> {summary}\n\n"
            f"Please check Teams and take over the conversation."
        )
        return self.send_message(text)

    def send_test(self) -> bool:
        return self.send_message("Teams Agent test message - notifications are working!")
