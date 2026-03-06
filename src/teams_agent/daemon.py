from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone

from rich.console import Console

from teams_agent.ai_responder import AIResponder
from teams_agent.config import load_config, load_env
from teams_agent.graph_client import GraphClient
from teams_agent.ignore_list import is_ignored
from teams_agent.models import Message
from teams_agent.telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)
console = Console()


class Daemon:
    def __init__(self) -> None:
        load_env()
        self._config = load_config()
        self._graph = GraphClient()
        self._ai = AIResponder(
            model=self._config.get("openai_model", "gpt-4"),
            system_prompt=self._config.get("system_prompt", ""),
        )
        self._telegram = TelegramNotifier()
        self._poll_interval = self._config.get("polling_interval", 10)
        self._severity_threshold = self._config.get("severity_threshold", 7)
        self._last_seen: dict[str, datetime] = {}
        self._running = False

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Received signal %s, shutting down...", signum)
        self._running = False

    def _get_new_messages(self, chat_id: str) -> list[Message]:
        since = self._last_seen.get(chat_id)
        messages = self._graph.get_messages(chat_id, since=since)
        if not messages:
            return []

        # Update last-seen to the newest message time
        newest = max(m.created for m in messages)
        self._last_seen[chat_id] = newest

        # Return only messages from others (not from us), sorted oldest first
        others = [m for m in messages if not m.is_from_me]
        others.sort(key=lambda m: m.created)
        return others

    def _process_message(self, new_msgs: list[Message], chat_id: str) -> None:
        if not new_msgs:
            return

        latest = new_msgs[-1]

        if is_ignored(latest.sender_email, latest.sender_name):
            logger.info("Ignoring message from %s (on ignore list)", latest.sender_name)
            return

        # Get recent conversation context for AI
        all_messages = self._graph.get_messages(chat_id, top=10)
        all_messages.sort(key=lambda m: m.created)

        console.print(f"[bold blue]New message from {latest.sender_name}:[/] {latest.body[:100]}")

        ai_response = self._ai.generate_response(all_messages)

        # Send reply
        self._graph.send_message(chat_id, ai_response.reply_text)
        console.print(f"[bold green]Replied:[/] {ai_response.reply_text[:100]}")
        logger.info(
            "Replied to %s in chat %s (severity: %d)",
            latest.sender_name, chat_id, ai_response.severity,
        )

        # Check severity and alert if needed
        if ai_response.severity >= self._severity_threshold:
            console.print(
                f"[bold red]High severity ({ai_response.severity}/10) detected![/] Notifying via Telegram..."
            )
            self._telegram.notify_tough_conversation(
                contact_name=latest.sender_name,
                severity=ai_response.severity,
                summary=ai_response.summary,
            )

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        self._running = True

        # Verify auth works
        me = self._graph.get_me()
        console.print(f"[bold green]Authenticated as:[/] {me.get('displayName', 'Unknown')}")
        console.print(f"Polling every {self._poll_interval}s. Press Ctrl+C to stop.\n")

        # Initialize last-seen for all chats to now (don't reply to old messages)
        now = datetime.now(timezone.utc)
        for chat in self._graph.list_chats():
            self._last_seen[chat["id"]] = now

        while self._running:
            try:
                chats = self._graph.list_chats()
                for chat in chats:
                    chat_id = chat["id"]
                    new_msgs = self._get_new_messages(chat_id)
                    if new_msgs:
                        self._process_message(new_msgs, chat_id)
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Error during polling cycle")

            time.sleep(self._poll_interval)

        console.print("\n[bold yellow]Daemon stopped.[/]")
