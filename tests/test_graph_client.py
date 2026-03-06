from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("AZURE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("AZURE_TENANT_ID", "fake-tenant-id")


@pytest.fixture
def client(mock_env, tmp_path, monkeypatch):
    import teams_agent.graph_client as gc

    monkeypatch.setattr(gc, "TOKEN_CACHE_FILE", tmp_path / "cache.json")

    with patch("msal.PublicClientApplication") as MockApp:
        mock_app = MagicMock()
        MockApp.return_value = mock_app
        c = gc.GraphClient()

    # The real app is our mock
    assert c._app is mock_app
    return c


class TestAuthenticateInteractive:
    def test_success(self, client):
        fake_result = {
            "access_token": "tok123",
            "id_token_claims": {"name": "Test User"},
        }
        client._app.acquire_token_interactive.return_value = fake_result

        result = client.authenticate_interactive()

        client._app.acquire_token_interactive.assert_called_once()
        call_kwargs = client._app.acquire_token_interactive.call_args
        assert call_kwargs.kwargs["prompt"] == "select_account"
        assert result["access_token"] == "tok123"

    def test_failure_raises(self, client):
        fake_result = {"error_description": "user cancelled"}
        client._app.acquire_token_interactive.return_value = fake_result

        with pytest.raises(RuntimeError, match="user cancelled"):
            client.authenticate_interactive()


class TestGetToken:
    def test_silent_success(self, client):
        fake_account = {"username": "user@test.com"}
        client._app.get_accounts.return_value = [fake_account]
        client._app.acquire_token_silent.return_value = {"access_token": "silent-tok"}

        token = client._get_token()

        assert token == "silent-tok"
        client._app.acquire_token_silent.assert_called_once()

    def test_silent_fail_falls_back_to_interactive(self, client):
        fake_account = {"username": "user@test.com"}
        client._app.get_accounts.return_value = [fake_account]
        client._app.acquire_token_silent.return_value = None
        client._app.acquire_token_interactive.return_value = {
            "access_token": "interactive-tok"
        }

        token = client._get_token()

        assert token == "interactive-tok"
        client._app.acquire_token_interactive.assert_called_once()

    def test_no_accounts_falls_back_to_interactive(self, client):
        client._app.get_accounts.return_value = []
        client._app.acquire_token_interactive.return_value = {
            "access_token": "interactive-tok"
        }

        token = client._get_token()

        assert token == "interactive-tok"
