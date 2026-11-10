"""Base entity for the peers of WGDashboard Monitor."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WGDashboardCoordinator


class WGDashboardPeerEntity(CoordinatorEntity[WGDashboardCoordinator]):
    """Entity of one peer: name translated in the Home Assistant language, with the peer name."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WGDashboardCoordinator, peer_id: str) -> None:
        super().__init__(coordinator)
        self._peer_id = peer_id
        self._attr_translation_placeholders = {"peer": self._peer_name()}

    @property
    def _peer(self) -> dict:
        return self.coordinator.data["peers"].get(self._peer_id, {})

    def _peer_name(self) -> str:
        return self._peer.get("name") or self._peer_id

    @property
    def available(self) -> bool:
        """A peer removed from WGDashboard becomes unavailable."""
        return super().available and self._peer_id in self.coordinator.data["peers"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """A peer renamed in WGDashboard gets its new name."""
        if self._peer_id in self.coordinator.data["peers"] and self._attr_translation_placeholders.get("peer") != self._peer_name():
            self._attr_translation_placeholders = {"peer": self._peer_name()}
            # le nom traduit est mis en cache par Home Assistant : il est recalculé avec le nouveau nom du peer
            self.__dict__.pop("name", None)
        super()._handle_coordinator_update()
