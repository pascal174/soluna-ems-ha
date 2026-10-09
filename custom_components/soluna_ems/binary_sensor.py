"""Aan/uit-toestanden: laadpaal, laadregelingen, auto, batterijgrenzen en meters."""
from __future__ import annotations

from dataclasses import dataclass, field
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
from .apparaat import apparaat_info, beschikbaar


@dataclass(frozen=True, kw_only=True)
class SolunaBinaryDescription(BinarySensorEntityDescription):
    pad: tuple[str, ...]
    test: Callable = bool
    meters: tuple[str, ...] = field(default=())
    online: tuple[str, ...] | None = None
    apparaat: str = "ems"


LAADPAAL = dict(online=("ev", "online"))

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
                            meters=("battery",),
                            pad=("battery", "limit"),
                            test=lambda v: v in ("min_soc", "max_soc", "unknown")),
    SolunaBinaryDescription(key="inverter_fault", name="Omvormerstoring",
                            device_class=BinarySensorDeviceClass.PROBLEM,
                            meters=("battery",),
                            pad=("battery", "has_fault")),

    # ── Laadpaal (sinds EMS 2.1.55) ────────────────────────────────────────────
    SolunaBinaryDescription(key="ev_online", name="Laadpaal bereikbaar",
                            device_class=BinarySensorDeviceClass.CONNECTIVITY,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("ev", "online")),
    SolunaBinaryDescription(key="ev_three_phase", name="Laadt op 3 fasen",
                            icon="mdi:sine-wave",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("ev", "three_phase"), **LAADPAAL),

    # ── Laadregelingen ─────────────────────────────────────────────────────────
    SolunaBinaryDescription(key="smart_enabled", name="Slim laden aan",
                            icon="mdi:calendar-clock", pad=("ev_smart", "enabled")),
    SolunaBinaryDescription(key="smart_active_slot", name="Slim laden in goedkoop uur",
                            device_class=BinarySensorDeviceClass.RUNNING,
                            pad=("ev_smart", "active_slot")),
    SolunaBinaryDescription(key="surplus_enabled", name="Overschot-laden aan",
                            icon="mdi:solar-power", pad=("ev_surplus", "enabled")),
    SolunaBinaryDescription(key="surplus_active", name="Overschot-laden actief",
                            device_class=BinarySensorDeviceClass.RUNNING,
                            pad=("ev_surplus", "active")),

    # ── Auto ───────────────────────────────────────────────────────────────────
    # Wat de auto zelf meldt bij de laatste uitlezing. Kan afwijken van wat de laadpaal
    # nu ziet, want deze integratie wekt de auto nooit om hem bij te werken.
    SolunaBinaryDescription(key="vehicle_charging", name="Laadt", apparaat="auto",
                            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
                            pad=("vehicle", "charging")),
    SolunaBinaryDescription(key="vehicle_plugged_in", name="Kabel aangesloten",
                            apparaat="auto", device_class=BinarySensorDeviceClass.PLUG,
                            pad=("vehicle", "plugged_in")),
    SolunaBinaryDescription(key="vehicle_tire_warning", name="Bandenspanning",
                            apparaat="auto", device_class=BinarySensorDeviceClass.PROBLEM,
                            icon="mdi:tire", pad=("vehicle", "tire_warning")),

    # ── Meters: of de EMS verse gegevens krijgt ────────────────────────────────
    *[SolunaBinaryDescription(key=f"meter_{groep}", name=f"{naam} verbonden",
                              device_class=BinarySensorDeviceClass.CONNECTIVITY,
                              entity_category=EntityCategory.DIAGNOSTIC,
                              pad=("meters", groep, "ok"))
      for groep, naam in (("grid", "Netmeter"), ("solar", "Zonnemeter"),
                          ("battery", "Batterij"))],
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
        self._attr_device_info = apparaat_info(coordinator, entry, beschrijving.apparaat)

    @property
    def available(self) -> bool:
        # Een meterverbinding is zelf de beschikbaarheidsmelding: die mag niet
        # verdwijnen op het moment dat hij 'uit' wordt, dan zie je de storing juist niet.
        if self.entity_description.pad[0] == "meters":
            return super().available and bool(
                self.coordinator.waarde("available", standaard=False))
        return super().available and beschikbaar(
            self.coordinator, self.entity_description.meters, self.entity_description.online)

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
