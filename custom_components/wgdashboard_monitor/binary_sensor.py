"""Binary sensor platform for WGDashboard Monitor."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WGDashboardCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WGDashboardCoordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_peers() -> None:
        """Peers added in WGDashboard after setup get their entity too."""
        new = [peer_id for peer_id in coordinator.data["peers"] if peer_id not in known]
        if new:
            known.update(new)
            async_add_entities(WGDashboardPeerConnectedSensor(coordinator, entry, peer_id) for peer_id in new)

    _add_new_peers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_peers))


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
    def available(self) -> bool:
        """A peer removed from WGDashboard becomes unavailable."""
        return super().available and self._peer_id in self.coordinator.data["peers"]

    @property
    def name(self) -> str:
        return f"{self._peer.get('name', self._peer_id)} connected"

    @property
    def is_on(self) -> bool:
        return bool(self._peer.get("online"))
