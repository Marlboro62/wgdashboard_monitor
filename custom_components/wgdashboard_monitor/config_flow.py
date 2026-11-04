"""Config flow for WGDashboard Monitor."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WGDashboardApiError, WGDashboardAuthError, WGDashboardClient
from .const import (
    CONF_API_KEY,
    CONF_CONFIG_NAME,
    CONF_HOST,
    CONF_VERIFY_SSL,
    DEFAULT_CONFIG_NAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_CONFIG_NAME, default=DEFAULT_CONFIG_NAME): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)
STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


def _valid_host(host: str) -> bool:
    url = urlparse(host.strip())
    return url.scheme in ("http", "https") and bool(url.netloc)


class WGDashboardMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WGDashboard Monitor."""

    VERSION = 1

    async def _test(self, data: Mapping[str, Any]) -> str | None:
        """Return an error key, or None when the host and API key work."""
        verify_ssl = data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        client = WGDashboardClient(
            async_get_clientsession(self.hass, verify_ssl=verify_ssl),
            data[CONF_HOST],
            data[CONF_API_KEY],
            verify_ssl,
        )
        try:
            await client.async_test_connection()
        except WGDashboardAuthError:
            return "invalid_auth"
        except WGDashboardApiError as err:
            _LOGGER.debug("WGDashboard connection test failed: %s", err)
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Host, API key and WireGuard configuration name."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().rstrip("/")
            config_name = user_input.get(CONF_CONFIG_NAME, DEFAULT_CONFIG_NAME)
            if not _valid_host(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            elif error := await self._test(user_input):
                errors["base"] = error
            else:
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}_{config_name}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"WGDashboard ({config_name})", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The API key was rejected: ask for a new one."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """New API key for an existing WGDashboard."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            if error := await self._test(data):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": entry.data[CONF_HOST]},
        )
