from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
import msal

from teams_agent.config import get_env
from teams_agent.models import Message

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Chat.ReadWrite", "ChatMessage.Read", "User.Read"]
TOKEN_CACHE_FILE = Path.home() / ".teams_agent_token_cache.json"


class GraphClient:
    def __init__(self) -> None:
        self._client_id = get_env("AZURE_CLIENT_ID")
        self._tenant_id = get_env("AZURE_TENANT_ID")
        self._authority = f"https://login.microsoftonline.com/{self._tenant_id}"
        self._cache = msal.SerializableTokenCache()
        self._load_cache()
        self._app = msal.PublicClientApplication(
            self._client_id,
            authority=self._authority,
            token_cache=self._cache,
        )
        self._http = httpx.Client(timeout=30)
        self._user_id: str | None = None

    def _load_cache(self) -> None:
        if TOKEN_CACHE_FILE.exists():
            self._cache.deserialize(TOKEN_CACHE_FILE.read_text())

    def _save_cache(self) -> None:
        if self._cache.has_state_changed:
            TOKEN_CACHE_FILE.write_text(self._cache.serialize())

    def _get_token(self) -> str:
        accounts = self._app.get_accounts()
        result = None
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result or "access_token" not in result:
            result = self.authenticate_interactive()
        self._save_cache()
        return result["access_token"]

    def authenticate_interactive(self) -> dict:
        result = self._app.acquire_token_interactive(
            scopes=SCOPES,
            prompt="select_account",
        )
        self._save_cache()
        if "access_token" not in result:
            raise RuntimeError(
                f"Authentication failed: {result.get('error_description', 'Unknown error')}"
            )
        return result

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def get_me(self) -> dict:
        resp = self._http.get(f"{GRAPH_BASE}/me", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        self._user_id = data.get("id")
        return data

    def get_my_id(self) -> str:
        if not self._user_id:
            self.get_me()
        return self._user_id  # type: ignore[return-value]

    def list_chats(self) -> list[dict]:
        resp = self._http.get(
            f"{GRAPH_BASE}/me/chats",
            headers=self._headers(),
            params={"$top": "50"},
        )
        resp.raise_for_status()
        return resp.json().get("value", [])

    def get_messages(
        self, chat_id: str, since: datetime | None = None, top: int = 20
    ) -> list[Message]:
        params: dict[str, str] = {
            "$top": str(top),
            "$orderby": "createdDateTime desc",
        }
        if since:
            iso = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            params["$filter"] = f"createdDateTime gt {iso}"

        resp = self._http.get(
            f"{GRAPH_BASE}/me/chats/{chat_id}/messages",
            headers=self._headers(),
            params=params,
        )
        resp.raise_for_status()

        my_id = self.get_my_id()
        messages: list[Message] = []
        for m in resp.json().get("value", []):
            if m.get("messageType") != "message":
                continue
            sender = m.get("from", {}).get("user", {})
            body_content = m.get("body", {}).get("content", "")
            created_str = m.get("createdDateTime", "")
            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created = datetime.now(timezone.utc)

            messages.append(
                Message(
                    id=m["id"],
                    chat_id=chat_id,
                    sender_email=sender.get("email", sender.get("userPrincipalName", "")),
                    sender_name=sender.get("displayName", "Unknown"),
                    body=body_content,
                    created=created,
                    is_from_me=sender.get("id") == my_id,
                )
            )
        return messages

    def send_message(self, chat_id: str, text: str) -> dict:
        resp = self._http.post(
            f"{GRAPH_BASE}/me/chats/{chat_id}/messages",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"body": {"content": text}},
        )
        resp.raise_for_status()
        return resp.json()
