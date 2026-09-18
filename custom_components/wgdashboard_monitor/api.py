"""Minimal async client for the WGDashboard REST API.

Reference: https://docs.wgdashboard.dev/api/
Note: WGDashboard's public docs are a work in progress and the exact
JSON shape can vary slightly between versions (3.x vs 4.x). This client
tries a couple of known endpoint/field name variants and falls back
gracefully; if your instance returns something different, check the
`raw` attribute exposed on the diagnostic sensor to adapt the parsing
in coordinator.py.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_HEADER_KEY

_LOGGER = logging.getLogger(__name__)


class WGDashboardApiError(Exception):
    """Raised when the WGDashboard API can't be reached or auth fails."""


class WGDashboardClient:
    """Thin wrapper around the WGDashboard REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        api_key: str,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self._base_url = host.rstrip("/")
        self._headers = {
            "content-type": "application/json",
            API_HEADER_KEY: api_key,
        }
        self._verify_ssl = verify_ssl

    async def _get(self, path: str, *, allow_404: bool = False) -> dict[str, Any] | None:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, ssl=self._verify_ssl, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 401:
                    raise WGDashboardApiError("Invalid or expired API key")
                if resp.status == 404 and allow_404:
                    return None
                if resp.status != 200:
                    raise WGDashboardApiError(f"Unexpected status {resp.status} from {url}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise WGDashboardApiError(f"Cannot reach WGDashboard at {url}: {err}") from err

    async def async_test_connection(self) -> bool:
        """Used by the config flow to validate host/api key."""
        await self._get("/api/getWireguardConfigurations")
        return True

    async def async_get_configurations(self) -> dict[str, Any]:
        """List all WireGuard configurations known to WGDashboard."""
        return await self._get("/api/getWireguardConfigurations")

    async def async_get_configuration_info(self, config_name: str) -> dict[str, Any]:
        """Detailed info (peers, handshakes, transfer) for one configuration.

        Confirmed via browser DevTools on WGDashboard 4.3.3:
        GET /api/getWireguardConfigurationInfo?configurationName=wg0
        (no trailing slash before the '?' - that trailing slash caused a 404).
        """
        from urllib.parse import quote

        name = quote(config_name)
        return await self._get(f"/api/getWireguardConfigurationInfo?configurationName={name}")
