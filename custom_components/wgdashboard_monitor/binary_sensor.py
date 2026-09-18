"""Binary sensor platform for WGDashboard Monitor."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WGDashboardCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WGDashboardCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        WGDashboardPeerConnectedSensor(coordinator, entry, peer_id)
        for peer_id in coordinator.data["peers"]
    ]
    async_add_entities(entities)


class WGDashboardPeerConnectedSensor(CoordinatorEntity[WGDashboardCoordinator], BinarySensorEntity):
    """Whether a peer's last handshake is recent enough to be 'connected'."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator: WGDashboardCoordinator, entry: ConfigEntry, peer_id: str) -> None:
        super().__init__(coordinator)
        self._peer_id = peer_id
        self._attr_unique_id = f"{entry.entry_id}_{peer_id}_connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="WGDashboard",
            model="WireGuard VPN",
        )

    @property
    def _peer(self) -> dict:
        return self.coordinator.data["peers"].get(self._peer_id, {})

    @property
    def name(self) -> str:
        return f"{self._peer.get('name', self._peer_id)} connected"

    @property
    def is_on(self) -> bool:
        return bool(self._peer.get("online"))
