"""Sensor platform for WGDashboard Monitor."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
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
        """Peers added in WGDashboard after setup get their entities too."""
        new = [peer_id for peer_id in coordinator.data["peers"] if peer_id not in known]
        if not new:
            return
        known.update(new)
        entities: list[SensorEntity] = []
        for peer_id in new:
            entities.append(WGDashboardPeerHandshakeSensor(coordinator, entry, peer_id))
            entities.append(WGDashboardPeerDataSensor(coordinator, entry, peer_id, "receive"))
            entities.append(WGDashboardPeerDataSensor(coordinator, entry, peer_id, "sent"))
        async_add_entities(entities)

    async_add_entities([WGDashboardConnectedCountSensor(coordinator, entry)])
    _add_new_peers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_peers))


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="WGDashboard",
        model="WireGuard VPN",
    )


class WGDashboardConnectedCountSensor(CoordinatorEntity[WGDashboardCoordinator], SensorEntity):
    """Number of peers currently connected."""

    _attr_icon = "mdi:vpn"
    _attr_has_entity_name = True
    _attr_name = "Connected peers"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WGDashboardCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connected_peers"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data["connected_peers"]

    @property
    def extra_state_attributes(self) -> dict:
        return {"total_peers": self.coordinator.data["total_peers"]}


class WGDashboardPeerHandshakeSensor(CoordinatorEntity[WGDashboardCoordinator], SensorEntity):
    """Last handshake timestamp for one peer."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:handshake"
    _attr_has_entity_name = True

    def __init__(self, coordinator: WGDashboardCoordinator, entry: ConfigEntry, peer_id: str) -> None:
        super().__init__(coordinator)
        self._peer_id = peer_id
        self._attr_unique_id = f"{entry.entry_id}_{peer_id}_last_handshake"
        self._attr_device_info = _device_info(entry)

    @property
    def _peer(self) -> dict:
        return self.coordinator.data["peers"].get(self._peer_id, {})

    @property
    def available(self) -> bool:
        """A peer removed from WGDashboard becomes unavailable."""
        return super().available and self._peer_id in self.coordinator.data["peers"]

    @property
    def name(self) -> str:
        return f"{self._peer.get('name', self._peer_id)} last handshake"

    @property
    def native_value(self):
        return self._peer.get("last_handshake")

    @property
    def extra_state_attributes(self) -> dict:
        peer = self._peer
        return {
            "endpoint": peer.get("endpoint"),
            "allowed_ips": peer.get("allowed_ips"),
        }


class WGDashboardPeerDataSensor(CoordinatorEntity[WGDashboardCoordinator], SensorEntity):
    """Cumulative data transfer for one peer (receive or sent), in GB."""

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_native_unit_of_measurement = UnitOfInformation.GIGABYTES
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: WGDashboardCoordinator, entry: ConfigEntry, peer_id: str, direction: str
    ) -> None:
        super().__init__(coordinator)
        self._peer_id = peer_id
        self._direction = direction  # "receive" or "sent"
        self._attr_icon = "mdi:download-network" if direction == "receive" else "mdi:upload-network"
        self._attr_unique_id = f"{entry.entry_id}_{peer_id}_{direction}"
        self._attr_device_info = _device_info(entry)

    @property
    def _peer(self) -> dict:
        return self.coordinator.data["peers"].get(self._peer_id, {})

    @property
    def available(self) -> bool:
        """A peer removed from WGDashboard becomes unavailable."""
        return super().available and self._peer_id in self.coordinator.data["peers"]

    @property
    def name(self) -> str:
        label = "data received" if self._direction == "receive" else "data sent"
        return f"{self._peer.get('name', self._peer_id)} {label}"

    @property
    def native_value(self) -> float | None:
        key = "total_receive_gb" if self._direction == "receive" else "total_sent_gb"
        return self._peer.get(key)
