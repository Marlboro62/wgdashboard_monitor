"""Config flow for WGDashboard Monitor."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WGDashboardApiError, WGDashboardClient
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
        vol.Required(CONF_HOST): str,  # e.g. http://192.168.1.14:10086
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_CONFIG_NAME, default=DEFAULT_CONFIG_NAME): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class WGDashboardMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WGDashboard Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass, verify_ssl=False)
            client = WGDashboardClient(
                session,
                user_input[CONF_HOST],
                user_input[CONF_API_KEY],
                user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            try:
                await client.async_test_connection()
            except WGDashboardApiError as err:
                _LOGGER.warning("WGDashboard connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                unique_id = f"{user_input[CONF_HOST]}_{user_input.get(CONF_CONFIG_NAME, DEFAULT_CONFIG_NAME)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                title = f"WGDashboard ({user_input.get(CONF_CONFIG_NAME, DEFAULT_CONFIG_NAME)})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)
