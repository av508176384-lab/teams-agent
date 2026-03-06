from __future__ import annotations

from teams_agent.config import load_config, save_config


def get_ignored() -> list[str]:
    config = load_config()
    return config.get("ignore_contacts", [])


def add_contact(email: str) -> bool:
    config = load_config()
    contacts = config.get("ignore_contacts", [])
    email_lower = email.lower()
    if email_lower in [c.lower() for c in contacts]:
        return False
    contacts.append(email_lower)
    config["ignore_contacts"] = contacts
    save_config(config)
    return True


def remove_contact(email: str) -> bool:
    config = load_config()
    contacts = config.get("ignore_contacts", [])
    email_lower = email.lower()
    new_contacts = [c for c in contacts if c.lower() != email_lower]
    if len(new_contacts) == len(contacts):
        return False
    config["ignore_contacts"] = new_contacts
    save_config(config)
    return True


def is_ignored(email: str, display_name: str = "") -> bool:
    contacts = get_ignored()
    lower_contacts = [c.lower() for c in contacts]
    return email.lower() in lower_contacts or (
        display_name and display_name.lower() in lower_contacts
    )
