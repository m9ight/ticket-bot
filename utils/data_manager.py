import json
import os
from typing import Any
from utils.logger import setup_logger

logger = setup_logger("data_manager")
_CACHE: dict[str, Any] = {}


def _load(path: str, default: Any) -> Any:
    if path in _CACHE:
        return _CACHE[path]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        _save(path, default)
        _CACHE[path] = default
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            _CACHE[path] = json.load(f)
            return _CACHE[path]
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load {path}: {e}")
        _CACHE[path] = default
        return default


def _save(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _CACHE[path] = data
    except IOError as e:
        logger.error(f"Failed to save {path}: {e}")


# ── Guild config ────────────────────────────────────────────────────────────

CONFIG_FILE = "data/guild_config.json"

def get_guild_config(guild_id: int) -> dict:
    data = _load(CONFIG_FILE, {})
    return data.get(str(guild_id), {})

def set_guild_config(guild_id: int, key: str, value: Any) -> None:
    data = _load(CONFIG_FILE, {})
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    data[gid][key] = value
    _save(CONFIG_FILE, data)

def get_config_value(guild_id: int, key: str, default: Any = None) -> Any:
    return get_guild_config(guild_id).get(key, default)


# ── Tickets ─────────────────────────────────────────────────────────────────

TICKETS_FILE = "data/tickets.json"

def get_tickets(guild_id: int) -> dict:
    data = _load(TICKETS_FILE, {})
    return data.get(str(guild_id), {"counter": 0, "open": {}})

def save_tickets(guild_id: int, tickets: dict) -> None:
    data = _load(TICKETS_FILE, {})
    data[str(guild_id)] = tickets
    _save(TICKETS_FILE, data)

def create_ticket(guild_id: int, channel_id: int, user_id: int, reason: str = "No reason provided") -> int:
    tickets = get_tickets(guild_id)
    tickets["counter"] = tickets.get("counter", 0) + 1
    ticket_id = tickets["counter"]
    tickets["open"][str(channel_id)] = {
        "id": ticket_id,
        "user_id": user_id,
        "channel_id": channel_id,
        "reason": reason,
    }
    save_tickets(guild_id, tickets)
    return ticket_id

def update_ticket_channel(guild_id: int, ticket_id: int, old_channel_id: int, new_channel_id: int) -> bool:
    tickets = get_tickets(guild_id)
    old_key = str(old_channel_id)
    ticket_data = tickets["open"].pop(old_key, None)
    if not ticket_data:
        return False
    ticket_data["channel_id"] = new_channel_id
    tickets["open"][str(new_channel_id)] = ticket_data
    save_tickets(guild_id, tickets)
    return True

def set_ticket_closed(guild_id: int, channel_id: int, closed: bool) -> bool:
    tickets = get_tickets(guild_id)
    key = str(channel_id)
    if key not in tickets["open"]:
        return False
    tickets["open"][key]["closed"] = closed
    save_tickets(guild_id, tickets)
    return True

def get_ticket_by_user(guild_id: int, user_id: int) -> tuple[int, dict] | None:
    tickets = get_tickets(guild_id)
    for channel_id, ticket in tickets["open"].items():
        if ticket.get("user_id") == user_id and not ticket.get("closed"):
            return int(channel_id), ticket
    return None

def get_ticket_by_channel(guild_id: int, channel_id: int) -> dict | None:
    tickets = get_tickets(guild_id)
    return tickets["open"].get(str(channel_id))

def close_ticket(guild_id: int, channel_id: int) -> bool:
    tickets = get_tickets(guild_id)
    key = str(channel_id)
    if key in tickets["open"]:
        del tickets["open"][key]
        save_tickets(guild_id, tickets)
        return True
    return False
