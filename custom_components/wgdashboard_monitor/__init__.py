"""The WGDashboard Monitor integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
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
)
from .coordinator import WGDashboardCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type WGDashboardConfigEntry = ConfigEntry[WGDashboardCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WGDashboardConfigEntry) -> bool:
    """Set up WGDashboard Monitor from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    client = WGDashboardClient(
        async_get_clientsession(hass, verify_ssl=verify_ssl),
        entry.data[CONF_HOST],
        entry.data[CONF_API_KEY],
        verify_ssl,
    )
    coordinator = WGDashboardCoordinator(
        hass, entry, client, entry.data.get(CONF_CONFIG_NAME, DEFAULT_CONFIG_NAME)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WGDashboardConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
