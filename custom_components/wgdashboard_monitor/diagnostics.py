"""Diagnostics for WGDashboard Monitor (Settings → Devices & services → ⋮ → Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_HOST

# API key, server address, peer keys, endpoints (public IPs) and allowed IPs are never shared
TO_REDACT = {CONF_API_KEY, CONF_HOST, "id", "endpoint", "allowed_ips", "name"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Configuration (redacted) and the normalized peer data."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "config_name": data.get("config_name"),
        "total_peers": data.get("total_peers"),
        "connected_peers": data.get("connected_peers"),
        "peers": [
            async_redact_data(
                {**peer, "last_handshake": peer["last_handshake"].isoformat() if peer.get("last_handshake") else None},
                TO_REDACT,
            )
            for peer in data.get("peers", {}).values()
        ],
    }
