from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


CONFIG_DIR = Path.cwd()
CONFIG_FILE = CONFIG_DIR / "config.yaml"
ENV_FILE = CONFIG_DIR / ".env"


def load_env() -> None:
    load_dotenv(ENV_FILE)


def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {
            "polling_interval": 10,
            "openai_model": "gpt-4",
            "severity_threshold": 7,
            "system_prompt": "You are a professional assistant replying on behalf of the user.",
            "ignore_contacts": [],
        }
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
