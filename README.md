# Teams Agent

CLI daemon that monitors Microsoft Teams messages, auto-replies using GPT, and sends Telegram alerts for high-severity conversations.

## Features

- Polls Teams chats for new messages and auto-replies via OpenAI GPT
- Browser-based SSO authentication with Microsoft Graph (no passwords or device codes)
- Telegram notifications when conversation severity exceeds a threshold
- Configurable ignore list for contacts
- Token caching for seamless re-authentication

## Prerequisites

- Python 3.11+
- An Azure AD app registration with the following:
  - **API permissions**: `Chat.ReadWrite`, `ChatMessage.Read`, `User.Read` (delegated)
  - **Redirect URI**: `http://localhost` under "Mobile and desktop applications" platform
- An OpenAI API key
- A Telegram bot token and chat ID (for alerts)

## Installation

```bash
pip install -e .
```

## Configuration

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

```
AZURE_CLIENT_ID=<your-azure-app-client-id>
AZURE_TENANT_ID=<your-azure-tenant-id>
OPENAI_API_KEY=<your-openai-key>
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

### config.yaml (optional)

Place a `config.yaml` in the working directory to customize behavior:

```yaml
polling_interval: 10
openai_model: gpt-4
severity_threshold: 7
system_prompt: "You are a professional assistant replying on behalf of the user."
ignore_contacts: []
```

## Usage

### Authenticate

Opens your system browser for Microsoft SSO. Reuses your existing login session — no password entry needed if you're already signed in.

```bash
teams-agent auth
```

### Start the daemon

```bash
teams-agent start
```

The daemon polls your Teams chats, generates GPT replies, and sends them automatically. If a conversation is rated high-severity, you get a Telegram alert.

If your token expires while the daemon is running, the browser opens automatically for re-authentication.

### Test Telegram

```bash
teams-agent test-telegram
```

### Manage ignore list

```bash
teams-agent ignore add user@example.com
teams-agent ignore remove user@example.com
teams-agent ignore list
```

### View config

```bash
teams-agent config
```

## Running tests

```bash
pip install pytest
pytest
```
