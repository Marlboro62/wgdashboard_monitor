"""Data update coordinator for WGDashboard Monitor."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WGDashboardApiError, WGDashboardClient
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Matches Python's str(timedelta) output, which is exactly what WGDashboard
# 4.3.x returns for `latest_handshake`, e.g. "0:01:29" or "1 day, 20:44:15".
_ELAPSED_RE = re.compile(r"(?:(\d+)\s+days?,\s*)?(\d+):(\d{2}):(\d{2})")


def _find_peer_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Try a few known WGDashboard response shapes to find the peer list."""
    data = payload.get("data", payload)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("configurationPeers", "Peers", "peers"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def _peer_field(peer: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in peer:
            return peer[name]
    return default


def _normalize_peer(peer: dict[str, Any]) -> dict[str, Any]:
    """Map a raw WGDashboard peer dict (v4.3.x shape) onto a stable set of fields."""
    name = _peer_field(peer, "name", "Name", default="")
    peer_id = _peer_field(peer, "id", "public_key", "PublicKey", default=name or "unknown")
    last_handshake_raw = _peer_field(peer, "latest_handshake", "LatestHandshake")
    endpoint = _peer_field(peer, "endpoint", "Endpoint", default="")
    status = _peer_field(peer, "status", "Status")
    # cumu_receive/cumu_sent are the lifetime totals shown on the peer cards
    # in the UI. total_receive/total_sent exist too but track something much
    # smaller (looks like the current session only) - not what we want here.
    total_receive = _peer_field(peer, "cumu_receive", "total_receive", default=0)
    total_sent = _peer_field(peer, "cumu_sent", "total_sent", default=0)
    allowed_ips = _peer_field(peer, "allowed_ip", "AllowedIPs", default="")

    last_handshake = _parse_elapsed_to_timestamp(last_handshake_raw)

    if isinstance(status, str):
        online = status.strip().lower() == "running"
    elif isinstance(status, bool):
        online = status
    else:
        online = last_handshake is not None

    return {
        "id": str(peer_id),
        "name": name or str(peer_id)[:8],
        "endpoint": endpoint,
        "allowed_ips": allowed_ips,
        "last_handshake": last_handshake,
        "total_receive_gb": _to_float(total_receive),
        "total_sent_gb": _to_float(total_sent),
        "online": online,
        "raw": peer,
    }


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_elapsed_to_timestamp(value: Any) -> datetime | None:
    """Turn a WGDashboard 'time since last handshake' string into a datetime.

    WGDashboard returns an elapsed-time string (Python's str(timedelta)
    format), e.g. "0:01:29" or "1 day, 20:44:15", or the literal
    "No Handshake" when the peer has never connected. We convert that
    elapsed time into an absolute UTC timestamp for HA's timestamp sensor.
    """
    if not value or not isinstance(value, str):
        return None
    if value.strip().lower() in ("no handshake", "(none)", "none", ""):
        return None

    match = _ELAPSED_RE.search(value)
    if not match:
        return None

    days, hours, minutes, seconds = match.groups()
    delta = timedelta(
        days=int(days or 0),
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
    )
    return datetime.now(timezone.utc) - delta


class WGDashboardCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls WGDashboard and exposes normalized peer data."""

    def __init__(self, hass: HomeAssistant, client: WGDashboardClient, config_name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="WGDashboard Monitor",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._client = client
        self._config_name = config_name

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            payload = await self._client.async_get_configuration_info(self._config_name)
        except WGDashboardApiError as err:
            raise UpdateFailed(str(err)) from err

        peers_raw = _find_peer_list(payload)
        peers = {p["id"]: p for p in (_normalize_peer(p) for p in peers_raw)}

        return {
            "config_name": self._config_name,
            "peers": peers,
            "total_peers": len(peers),
            "connected_peers": sum(1 for p in peers.values() if p["online"]),
            "raw": payload,
        }

