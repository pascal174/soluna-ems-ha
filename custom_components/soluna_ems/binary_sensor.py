"""Aan/uit-toestanden: laadpaal en batterijgrenzen."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolunaCoordinator


@dataclass(frozen=True, kw_only=True)
class SolunaBinaryDescription(BinarySensorEntityDescription):
    pad: tuple[str, ...]
    test: Callable = bool


BINAIR: tuple[SolunaBinaryDescription, ...] = (
    SolunaBinaryDescription(key="ev_plugged_in", name="Laadpaal aangesloten",
                            device_class=BinarySensorDeviceClass.PLUG,
                            pad=("ev", "plugged_in")),
    SolunaBinaryDescription(key="ev_charging", name="Auto laadt",
                            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
                            pad=("ev", "charging")),
    # De batterij kan niet verder ontladen (reservegrens) of niets meer opnemen (vol).
    # Handig om op te automatiseren: dán volgt de meter het huisverbruik ongedempt.
    SolunaBinaryDescription(key="battery_at_limit", name="Batterij op een grens",
                            device_class=BinarySensorDeviceClass.PROBLEM,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("battery", "limit"),
                            test=lambda v: v in ("min_soc", "max_soc", "unknown")),
    SolunaBinaryDescription(key="inverter_fault", name="Omvormerstoring",
                            device_class=BinarySensorDeviceClass.PROBLEM,
                            pad=("battery", "has_fault")),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: SolunaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SolunaBinarySensor(coordinator, entry, b) for b in BINAIR
        if coordinator.waarde(*b.pad) is not None
    )


class SolunaBinarySensor(CoordinatorEntity[SolunaCoordinator], BinarySensorEntity):
    entity_description: SolunaBinaryDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, beschrijving: SolunaBinaryDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = beschrijving
        self._attr_unique_id = f"{entry.entry_id}_{beschrijving.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Soluna",
            "model": "Soluna EMS",
        }

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.waarde("available", standaard=False))

    @property
    def is_on(self) -> bool:
        return bool(self.entity_description.test(
            self.coordinator.waarde(*self.entity_description.pad)))

    @property
    def extra_state_attributes(self) -> dict:
        if self.entity_description.key != "battery_at_limit":
            return {}
        grens = self.coordinator.waarde("battery", "limit", standaard="")
        return {"reden": {"min_soc": "Op de reservegrens — kan niet verder ontladen",
                          "max_soc": "Vol — kan geen overschot meer opnemen",
                          "unknown": "Laadtoestand onbekend"}.get(grens, "")}
