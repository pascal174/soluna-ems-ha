"""Gedeeld door de bedien-entiteiten (schakelaars, schuiven, keuzelijsten, knoppen).

Elke actie gaat naar `/api/ha/control` op de EMS en loopt daar via hetzelfde endpoint als
een klik op het dashboard. De EMS houdt dus de grenzen bij (paal-maximum, SoC van de accu,
handbediening zet slim laden uit); deze integratie dupliceert die regels niet.

Wat hier bewust níet in zit: iets wat de auto wekt of uitleest.
"""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .apparaat import apparaat_info
from .coordinator import SolunaCoordinator


class SolunaBediening(CoordinatorEntity[SolunaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sleutel: str, naam: str, icoon: str | None = None) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_bediening_{sleutel}"
        self._attr_name = naam
        self._attr_icon = icoon
        self._attr_device_info = apparaat_info(coordinator, entry, "ems")

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.waarde("available", standaard=False))


def heeft_laadpaal(coordinator) -> bool:
    return coordinator.waarde("control", "charger_id") is not None


def heeft_accu(coordinator) -> bool:
    return coordinator.waarde("control", "battery_max_charge_w") is not None
