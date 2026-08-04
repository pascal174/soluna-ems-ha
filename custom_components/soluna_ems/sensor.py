"""Sensoren van de Soluna EMS.

Alle waarden komen uit één statusdocument. Een sensor wordt alleen aangemaakt als de
installatie die waarde ook echt levert — zonder batterij of zonder gasaansluiting
verschijnen die entiteiten dus niet, in plaats van eeuwig op 'onbekend' te blijven staan.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolunaCoordinator

# Leesbare namen voor de strategie, gelijk aan wat het EMS-dashboard toont.
STRATEGIE_LABELS = {
    "balance": "Balanceren", "inject_only": "Alleen injectie", "discharge": "Ontladen",
    "charge": "Opladen", "peak_shave": "Piekscheren", "no_inject": "Geen injectie",
    "charge_no_inject": "Opladen (geen injectie)", "grid_only": "Alleen afname",
    "no_inject_no_charge": "Geen injectie (niet laden)",
    "charge_grid_only": "Opladen (enkel afname)", "idle": "Inactief", "manual": "Handmatig",
}


@dataclass(frozen=True, kw_only=True)
class SolunaSensorDescription(SensorEntityDescription):
    """Sensorbeschrijving met een pad in het statusdocument."""
    pad: tuple[str, ...]
    omzetter: Callable | None = None


def _fase(nummer: int, veld: str):
    """Haal een fasewaarde uit de lijst die de P1-meter levert."""
    def lezer(data):
        for f in (data or []):
            if f.get("phase") == f"L{nummer}":
                return f.get(veld)
        return None
    return lezer


VERMOGEN = dict(device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
                state_class=SensorStateClass.MEASUREMENT)
ENERGIE_TOTAAL = dict(device_class=SensorDeviceClass.ENERGY,
                      native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                      state_class=SensorStateClass.TOTAL_INCREASING)
ENERGIE_DAG = dict(device_class=SensorDeviceClass.ENERGY,
                   native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                   state_class=SensorStateClass.TOTAL_INCREASING)
TEMPERATUUR = dict(device_class=SensorDeviceClass.TEMPERATURE,
                   native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                   state_class=SensorStateClass.MEASUREMENT,
                   entity_category=EntityCategory.DIAGNOSTIC)
SPANNING = dict(device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC)
STROOM = dict(device_class=SensorDeviceClass.CURRENT,
              native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
              state_class=SensorStateClass.MEASUREMENT,
              entity_category=EntityCategory.DIAGNOSTIC)
PRIJS = dict(native_unit_of_measurement="EUR/kWh", state_class=SensorStateClass.MEASUREMENT)
GELD = dict(device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement="EUR",
            state_class=SensorStateClass.TOTAL)

SENSOREN: tuple[SolunaSensorDescription, ...] = (
    # ── Live vermogens ─────────────────────────────────────────────────────────
    SolunaSensorDescription(key="solar_power", name="Zonne-vermogen",
                            icon="mdi:solar-power", pad=("power", "solar_w"), **VERMOGEN),
    SolunaSensorDescription(key="grid_power", name="Netvermogen",
                            icon="mdi:transmission-tower", pad=("power", "grid_w"), **VERMOGEN),
    SolunaSensorDescription(key="battery_power", name="Batterijvermogen",
                            icon="mdi:battery-charging", pad=("power", "battery_w"), **VERMOGEN),
    SolunaSensorDescription(key="house_power", name="Huisverbruik",
                            icon="mdi:home-lightning-bolt", pad=("power", "house_w"), **VERMOGEN),
    SolunaSensorDescription(key="ev_power", name="Laadpaal-vermogen",
                            icon="mdi:ev-station", pad=("power", "ev_w"), **VERMOGEN),

    # ── Batterij ───────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="battery_soc", name="Batterij laadtoestand",
                            device_class=SensorDeviceClass.BATTERY,
                            native_unit_of_measurement=PERCENTAGE,
                            state_class=SensorStateClass.MEASUREMENT,
                            pad=("battery", "soc_pct")),
    SolunaSensorDescription(key="battery_state", name="Batterij status",
                            icon="mdi:state-machine", pad=("battery", "state_name")),
    SolunaSensorDescription(key="battery_temp", name="Batterijtemperatuur",
                            pad=("battery", "battery_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="inverter_temp", name="Omvormertemperatuur",
                            pad=("battery", "inverter_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="heatsink_temp", name="Koellichaamtemperatuur",
                            pad=("battery", "heatsink_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="battery_voltage", name="Accuspanning",
                            pad=("battery", "battery_voltage"), **SPANNING),
    SolunaSensorDescription(key="battery_current", name="Accustroom",
                            pad=("battery", "battery_current"), **STROOM),
    SolunaSensorDescription(key="battery_cycles", name="Laadcycli",
                            icon="mdi:battery-sync", entity_category=EntityCategory.DIAGNOSTIC,
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            pad=("battery", "battery_cycles")),

    # ── Sturing ────────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="strategy", name="Strategie", icon="mdi:strategy",
                            pad=("mode", "strategy"),
                            omzetter=lambda v: STRATEGIE_LABELS.get(v, v)),
    SolunaSensorDescription(key="control_mode", name="Sturingsmodus", icon="mdi:tune",
                            pad=("mode", "control_mode"),
                            omzetter=lambda v: {"auto": "Automatisch",
                                                "manual": "Handmatig"}.get(v, v)),
    SolunaSensorDescription(key="optimizer_source", name="Optimizer-bron", icon="mdi:brain",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("mode", "optimizer_source"),
                            omzetter=lambda v: {"ai": "AI", "rule": "Regelgebaseerd"}.get(v, v)),

    # ── Prijzen ────────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="price_now", name="Stroomprijs nu", icon="mdi:cash",
                            pad=("price", "now_eur_kwh"), **PRIJS),
    SolunaSensorDescription(key="price_min", name="Laagste prijs vandaag", icon="mdi:cash-minus",
                            pad=("price", "today_min_eur_kwh"), **PRIJS),
    SolunaSensorDescription(key="price_max", name="Hoogste prijs vandaag", icon="mdi:cash-plus",
                            pad=("price", "today_max_eur_kwh"), **PRIJS),
    SolunaSensorDescription(key="price_avg", name="Gemiddelde prijs vandaag", icon="mdi:cash",
                            pad=("price", "today_avg_eur_kwh"), **PRIJS),

    # ── Meterstanden (voor het energiedashboard van Home Assistant) ────────────
    SolunaSensorDescription(key="grid_import_total", name="Net afgenomen totaal",
                            icon="mdi:transmission-tower-import",
                            pad=("counters", "grid_import_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="grid_export_total", name="Net teruggeleverd totaal",
                            icon="mdi:transmission-tower-export",
                            pad=("counters", "grid_export_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="solar_total", name="Zonopbrengst totaal",
                            icon="mdi:solar-power-variant",
                            pad=("counters", "solar_total_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="gas_total", name="Gasverbruik totaal", icon="mdi:fire",
                            device_class=SensorDeviceClass.GAS,
                            native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            pad=("counters", "gas_m3")),

    # ── Dagtotalen ─────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="today_solar", name="Zon vandaag", icon="mdi:solar-power",
                            pad=("today", "solar_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_house", name="Verbruik vandaag", icon="mdi:home",
                            pad=("today", "house_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_import", name="Afname vandaag",
                            icon="mdi:transmission-tower-import",
                            pad=("today", "import_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_export", name="Teruglevering vandaag",
                            icon="mdi:transmission-tower-export",
                            pad=("today", "export_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_charge", name="Batterij geladen vandaag",
                            icon="mdi:battery-arrow-up",
                            pad=("today", "battery_charge_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_discharge", name="Batterij ontladen vandaag",
                            icon="mdi:battery-arrow-down",
                            pad=("today", "battery_discharge_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="today_cost", name="Kosten afname vandaag",
                            icon="mdi:cash-minus", pad=("today", "cost_import_eur"), **GELD),
    SolunaSensorDescription(key="today_revenue", name="Opbrengst teruglevering vandaag",
                            icon="mdi:cash-plus", pad=("today", "revenue_export_eur"), **GELD),

    # ── Zonverwachting ─────────────────────────────────────────────────────────
    SolunaSensorDescription(key="forecast_today", name="Zonverwachting vandaag",
                            icon="mdi:weather-sunny",
                            device_class=SensorDeviceClass.ENERGY,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            pad=("forecast", "today_kwh")),
    SolunaSensorDescription(key="forecast_tomorrow", name="Zonverwachting morgen",
                            icon="mdi:weather-sunny",
                            device_class=SensorDeviceClass.ENERGY,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            pad=("forecast", "tomorrow_kwh")),

    # ── Netdetails per fase ────────────────────────────────────────────────────
    *[SolunaSensorDescription(key=f"grid_l{i}_voltage", name=f"Netspanning L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "voltage_v"),
                              **SPANNING) for i in (1, 2, 3)],
    *[SolunaSensorDescription(key=f"grid_l{i}_current", name=f"Netstroom L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "current_a"),
                              **STROOM) for i in (1, 2, 3)],
    *[SolunaSensorDescription(key=f"grid_l{i}_power", name=f"Netvermogen L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "power_w"),
                              entity_category=EntityCategory.DIAGNOSTIC, **VERMOGEN)
      for i in (1, 2, 3)],
    SolunaSensorDescription(key="grid_tariff", name="Actief tarief", icon="mdi:clock-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("grid_detail", "tariff"),
                            omzetter=lambda v: {1: "Dal", 2: "Piek"}.get(v, v)),

    # ── Zonnemeter ─────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="solar_frequency", name="Netfrequentie (zonnemeter)",
                            device_class=SensorDeviceClass.FREQUENCY,
                            native_unit_of_measurement=UnitOfFrequency.HERTZ,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("solar_detail", "Freq")),
    SolunaSensorDescription(key="solar_power_factor", name="Arbeidsfactor (zonnemeter)",
                            device_class=SensorDeviceClass.POWER_FACTOR,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("solar_detail", "PFt")),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: SolunaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entiteiten = []
    for beschrijving in SENSOREN:
        # Alleen aanmaken als de EMS deze waarde ook levert.
        ruw = coordinator.waarde(*beschrijving.pad)
        if beschrijving.omzetter is not None and beschrijving.pad[-1] == "phases":
            ruw = beschrijving.omzetter(ruw)
        if ruw is None:
            continue
        entiteiten.append(SolunaSensor(coordinator, entry, beschrijving))
    async_add_entities(entiteiten)


class SolunaSensor(CoordinatorEntity[SolunaCoordinator], SensorEntity):
    entity_description: SolunaSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, beschrijving: SolunaSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = beschrijving
        self._attr_unique_id = f"{entry.entry_id}_{beschrijving.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Soluna",
            "model": "Soluna EMS",
            "configuration_url": f"http://{coordinator.host}:5555/",
        }

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.waarde("available", standaard=False))

    @property
    def native_value(self):
        waarde = self.coordinator.waarde(*self.entity_description.pad)
        if self.entity_description.omzetter is not None:
            waarde = self.entity_description.omzetter(waarde)
        return waarde
