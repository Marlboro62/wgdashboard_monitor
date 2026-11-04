"""Minimal async client for the WGDashboard REST API.

Reference: https://docs.wgdashboard.dev/api/
The JSON shape can vary slightly between WGDashboard versions (3.x / 4.x):
coordinator.py tries the known field names. Enable debug logging for
custom_components.wgdashboard_monitor to see the raw response.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_HEADER_KEY

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class WGDashboardApiError(Exception):
    """Raised when the WGDashboard API can't be reached or returns an error."""


class WGDashboardAuthError(WGDashboardApiError):
    """Raised when the API key is rejected."""


class WGDashboardClient:
    """Thin wrapper around the WGDashboard REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        api_key: str,
        verify_ssl: bool = True,
    ) -> None:
        self._session = session
        self._base_url = host.strip().rstrip("/")
        self._headers = {
            "content-type": "application/json",
            API_HEADER_KEY: api_key,
        }
        # False disables certificate checks (self-signed HTTPS); None keeps the default checks
        self._ssl: bool | None = None if verify_ssl else False

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, params=params, ssl=self._ssl, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status in (401, 403):
                    raise WGDashboardAuthError("Invalid or expired API key")
                if resp.status != 200:
                    raise WGDashboardApiError(f"Unexpected status {resp.status} from {path}")
                payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise WGDashboardApiError(f"Cannot reach WGDashboard: {err}") from err
        except ValueError as err:
            raise WGDashboardApiError(f"Invalid JSON from {path}") from err
        if not isinstance(payload, dict):
            raise WGDashboardApiError(f"Unexpected response from {path}")
        if payload.get("status") is False:
            raise WGDashboardApiError(str(payload.get("message") or f"Request {path} refused"))
        return payload

    async def async_test_connection(self) -> bool:
        """Used by the config flow to validate host and API key."""
        await self._get("/api/getWireguardConfigurations")
        return True

    async def async_get_configuration_info(self, config_name: str) -> dict[str, Any]:
        """Peers, handshakes and transfer totals for one configuration.

        WGDashboard 4.3.x: GET /api/getWireguardConfigurationInfo?configurationName=wg0
        """
        return await self._get(
            "/api/getWireguardConfigurationInfo", {"configurationName": config_name}
        )
