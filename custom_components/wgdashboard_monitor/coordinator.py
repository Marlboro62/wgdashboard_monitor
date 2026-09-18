"""Data update coordinator for WGDashboard Monitor."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WGDashboardApiError, WGDashboardClient
from .const import DEFAULT_SCAN_INTERVAL, HANDSHAKE_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)


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
    """Map a raw WGDashboard peer dict onto a stable set of fields."""
    name = _peer_field(peer, "name", "Name", default="")
    peer_id = _peer_field(peer, "id", "public_key", "PublicKey", default=name or "unknown")
    last_handshake_raw = _peer_field(peer, "latest_handshake", "LatestHandshake", "latest_handshake_at")
    endpoint = _peer_field(peer, "endpoint", "Endpoint", default="")
    total_receive = _peer_field(peer, "total_receive", "TotalReceive", "cumu_receive", default=0)
    total_sent = _peer_field(peer, "total_sent", "TotalSent", "cumu_sent", default=0)
    allowed_ips = _peer_field(peer, "allowed_ip", "AllowedIPs", default="")

    last_handshake = _parse_timestamp(last_handshake_raw)
    online = _is_recent(last_handshake)

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


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _is_recent(last_handshake: datetime | None) -> bool:
    if last_handshake is None:
        return False
    age = datetime.now(timezone.utc) - last_handshake
    return age.total_seconds() < HANDSHAKE_TIMEOUT_SECONDS


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
