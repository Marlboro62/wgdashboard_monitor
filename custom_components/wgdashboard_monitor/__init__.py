"""The WGDashboard Monitor integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WGDashboardClient
from .const import (
    CONF_API_KEY,
    CONF_CONFIG_NAME,
    CONF_HOST,
    CONF_VERIFY_SSL,
    DEFAULT_CONFIG_NAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import WGDashboardCoordinator

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )
    client = WGDashboardClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_API_KEY],
        entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    config_name = entry.data.get(CONF_CONFIG_NAME, DEFAULT_CONFIG_NAME)
    coordinator = WGDashboardCoordinator(hass, client, config_name)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
