"""Sensoren van de Soluna EMS.

Alle waarden komen uit één statusdocument. Een sensor wordt alleen aangemaakt als de
installatie die waarde ook echt levert — zonder batterij of zonder gasaansluiting
verschijnen die entiteiten dus niet, in plaats van eeuwig op 'onbekend' te blijven staan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SolunaCoordinator
from .apparaat import apparaat_info, beschikbaar

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
    """Sensorbeschrijving met een pad in het statusdocument.

    `meters`: van welke meetgroepen ("grid", "solar", "battery") deze waarde afhangt. Is
    een daarvan niet vers, dan wordt de sensor 'niet beschikbaar' in plaats van de laatste
    waarde te blijven tonen alsof er niets aan de hand is.
    `online`: een pad dat niet False mag zijn (bv. of de laadpaal bereikbaar is).
    `apparaat`: "ems" of "auto" — de auto krijgt een eigen apparaat.
    `altijd`: aanmaken zodra het omringende blok bestaat, ook als de waarde nu leeg is.
    Nodig voor tijdstippen van gebeurtenissen die nog nooit zijn voorgekomen; anders
    verschijnt de sensor pas na een herstart van Home Assistant.
    """
    pad: tuple[str, ...]
    omzetter: Callable | None = None
    meters: tuple[str, ...] = field(default=())
    online: tuple[str, ...] | None = None
    apparaat: str = "ems"
    altijd: bool = False


def _tijdstip(waarde):
    """ISO-tekst met tijdzone → datetime voor een TIMESTAMP-sensor."""
    if not waarde:
        return None
    return dt_util.parse_datetime(str(waarde))


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
VERMOGEN_KW = dict(device_class=SensorDeviceClass.POWER,
                   native_unit_of_measurement=UnitOfPower.KILO_WATT,
                   state_class=SensorStateClass.MEASUREMENT)
# Opgeslagen energie (accu van de auto, nog te laden). Geen TOTAL: het gaat op en neer.
ENERGIE_OPSLAG = dict(device_class=SensorDeviceClass.ENERGY_STORAGE,
                      native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                      state_class=SensorStateClass.MEASUREMENT)
BANDENSPANNING = dict(device_class=SensorDeviceClass.PRESSURE,
                      native_unit_of_measurement=UnitOfPressure.BAR,
                      state_class=SensorStateClass.MEASUREMENT)
TIJDSTIP = dict(device_class=SensorDeviceClass.TIMESTAMP, omzetter=_tijdstip)
# Live laadpaalwaarden zijn alleen zinvol als de laadpaal bereikbaar is.
LAADPAAL = dict(online=("ev", "online"))
GELD = dict(device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement="EUR",
            state_class=SensorStateClass.TOTAL)

SENSOREN: tuple[SolunaSensorDescription, ...] = (
    # ── Live vermogens ─────────────────────────────────────────────────────────
    SolunaSensorDescription(key="solar_power", meters=('solar',), name="Zonne-vermogen",
                            icon="mdi:solar-power", pad=("power", "solar_w"), **VERMOGEN),
    SolunaSensorDescription(key="grid_power", meters=('grid',), name="Netvermogen",
                            icon="mdi:transmission-tower", pad=("power", "grid_w"), **VERMOGEN),
    SolunaSensorDescription(key="battery_power", meters=('battery',), name="Batterijvermogen",
                            icon="mdi:battery-charging", pad=("power", "battery_w"), **VERMOGEN),
    SolunaSensorDescription(key="house_power", meters=('grid', 'solar', 'battery'), name="Huisverbruik",
                            icon="mdi:home-lightning-bolt", pad=("power", "house_w"), **VERMOGEN),
    SolunaSensorDescription(key="ev_power", name="Laadpaal-vermogen",
                            icon="mdi:ev-station", pad=("power", "ev_w"), **VERMOGEN),

    # ── Batterij ───────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="battery_soc", meters=('battery',), name="Batterij laadtoestand",
                            device_class=SensorDeviceClass.BATTERY,
                            native_unit_of_measurement=PERCENTAGE,
                            state_class=SensorStateClass.MEASUREMENT,
                            pad=("battery", "soc_pct")),
    SolunaSensorDescription(key="battery_state", meters=('battery',), name="Batterij status",
                            icon="mdi:state-machine", pad=("battery", "state_name")),
    SolunaSensorDescription(key="battery_temp", meters=('battery',), name="Batterijtemperatuur",
                            pad=("battery", "battery_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="inverter_temp", meters=('battery',), name="Omvormertemperatuur",
                            pad=("battery", "inverter_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="heatsink_temp", meters=('battery',), name="Koellichaamtemperatuur",
                            pad=("battery", "heatsink_temp"), **TEMPERATUUR),
    SolunaSensorDescription(key="battery_voltage", meters=('battery',), name="Accuspanning",
                            pad=("battery", "battery_voltage"), **SPANNING),
    SolunaSensorDescription(key="battery_current", meters=('battery',), name="Accustroom",
                            pad=("battery", "battery_current"), **STROOM),
    SolunaSensorDescription(key="battery_cycles", meters=('battery',), name="Laadcycli",
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
    SolunaSensorDescription(key="grid_import_total", meters=('grid',), name="Net afgenomen totaal",
                            icon="mdi:transmission-tower-import",
                            pad=("counters", "grid_import_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="grid_export_total", meters=('grid',), name="Net teruggeleverd totaal",
                            icon="mdi:transmission-tower-export",
                            pad=("counters", "grid_export_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="solar_total", meters=('solar',), name="Zonopbrengst totaal",
                            icon="mdi:solar-power-variant",
                            pad=("counters", "solar_total_kwh"), **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="gas_total", meters=('grid',), name="Gasverbruik totaal", icon="mdi:fire",
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
    *[SolunaSensorDescription(key=f"grid_l{i}_voltage", meters=("grid",), name=f"Netspanning L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "voltage_v"),
                              **SPANNING) for i in (1, 2, 3)],
    *[SolunaSensorDescription(key=f"grid_l{i}_current", meters=("grid",), name=f"Netstroom L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "current_a"),
                              **STROOM) for i in (1, 2, 3)],
    *[SolunaSensorDescription(key=f"grid_l{i}_power", meters=("grid",), name=f"Netvermogen L{i}",
                              pad=("grid_detail", "phases"), omzetter=_fase(i, "power_w"),
                              entity_category=EntityCategory.DIAGNOSTIC, **VERMOGEN)
      for i in (1, 2, 3)],
    SolunaSensorDescription(key="grid_tariff", meters=('grid',), name="Actief tarief", icon="mdi:clock-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("grid_detail", "tariff"),
                            omzetter=lambda v: {1: "Dal", 2: "Piek"}.get(v, v)),

    # ── Zonnemeter ─────────────────────────────────────────────────────────────
    SolunaSensorDescription(key="solar_frequency", meters=('solar',), name="Netfrequentie (zonnemeter)",
                            device_class=SensorDeviceClass.FREQUENCY,
                            native_unit_of_measurement=UnitOfFrequency.HERTZ,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("solar_detail", "Freq")),
    SolunaSensorDescription(key="solar_power_factor", meters=('solar',), name="Arbeidsfactor (zonnemeter)",
                            device_class=SensorDeviceClass.POWER_FACTOR,
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("solar_detail", "PFt")),

    # ── Laadpaal (sinds EMS 2.1.55) ────────────────────────────────────────────
    SolunaSensorDescription(key="ev_confirmed_power", name="Laadpaal ingesteld vermogen",
                            icon="mdi:ev-station", pad=("ev", "confirmed_kw"),
                            **VERMOGEN_KW, **LAADPAAL),
    SolunaSensorDescription(key="ev_error", name="Laadpaal storingscode",
                            icon="mdi:alert-circle-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("ev", "error"), **LAADPAAL),
    # De meterstand van de laadpaal loopt levenslang op: geschikt voor het
    # energiedashboard van Home Assistant, als apparaatverbruik.
    SolunaSensorDescription(key="ev_energy_total", name="Laadpaal meterstand",
                            icon="mdi:counter", pad=("ev", "energy_total_kwh"),
                            **ENERGIE_TOTAAL),
    SolunaSensorDescription(key="ev_today_energy", name="Auto geladen vandaag",
                            icon="mdi:car-electric", pad=("ev", "today_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="ev_today_grid_energy", name="Auto geladen van het net vandaag",
                            icon="mdi:transmission-tower-import",
                            pad=("ev", "today_grid_kwh"), **ENERGIE_DAG),
    SolunaSensorDescription(key="ev_today_cost", name="Laadkosten vandaag",
                            icon="mdi:cash", pad=("ev", "today_cost_eur"), **GELD),

    # ── Slim laden en overschot-laden ──────────────────────────────────────────
    SolunaSensorDescription(key="smart_state", name="Slim laden status",
                            icon="mdi:calendar-clock", pad=("ev_smart", "state")),
    SolunaSensorDescription(key="smart_target", name="Slim laden doel",
                            icon="mdi:target", device_class=SensorDeviceClass.ENERGY,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            pad=("ev_smart", "target_kwh")),
    SolunaSensorDescription(key="smart_progress", name="Slim laden voortgang",
                            icon="mdi:progress-check", device_class=SensorDeviceClass.ENERGY,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            pad=("ev_smart", "progress_kwh")),
    SolunaSensorDescription(key="smart_deadline", name="Slim laden klaar om",
                            icon="mdi:clock-end", pad=("ev_smart", "deadline"),
                            altijd=True, **TIJDSTIP),
    SolunaSensorDescription(key="surplus_power", name="Overschot-laden vermogen",
                            icon="mdi:solar-power", pad=("ev_surplus", "power_kw"),
                            **VERMOGEN_KW),
    # Alleen bij een laadpaal met een pauzebudget (Peblar): hoe vaak hij de komende
    # tien minuten nog mag pauzeren.
    SolunaSensorDescription(key="surplus_pause_budget", name="Pauzes over",
                            icon="mdi:pause-circle-outline",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("ev_surplus", "pause_budget_left")),

    # ── Auto (eigen apparaat; de gegevens worden nooit door deze integratie ververst)
    SolunaSensorDescription(key="vehicle_soc", name="Accu", apparaat="auto",
                            device_class=SensorDeviceClass.BATTERY,
                            native_unit_of_measurement=PERCENTAGE,
                            state_class=SensorStateClass.MEASUREMENT,
                            pad=("vehicle", "soc_pct")),
    SolunaSensorDescription(key="vehicle_range", name="Actieradius", apparaat="auto",
                            icon="mdi:map-marker-distance",
                            device_class=SensorDeviceClass.DISTANCE,
                            native_unit_of_measurement=UnitOfLength.KILOMETERS,
                            state_class=SensorStateClass.MEASUREMENT,
                            pad=("vehicle", "range_km")),
    SolunaSensorDescription(key="vehicle_odometer", name="Kilometerstand", apparaat="auto",
                            icon="mdi:counter", device_class=SensorDeviceClass.DISTANCE,
                            native_unit_of_measurement=UnitOfLength.KILOMETERS,
                            state_class=SensorStateClass.TOTAL_INCREASING,
                            pad=("vehicle", "odometer_km")),
    SolunaSensorDescription(key="vehicle_energy", name="Energie in de accu", apparaat="auto",
                            pad=("vehicle", "energy_kwh"), **ENERGIE_OPSLAG),
    SolunaSensorDescription(key="vehicle_energy_to_full", name="Nog te laden", apparaat="auto",
                            icon="mdi:battery-arrow-up",
                            pad=("vehicle", "energy_to_full_kwh"), **ENERGIE_OPSLAG),
    SolunaSensorDescription(key="vehicle_capacity", name="Accucapaciteit", apparaat="auto",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENERGY_STORAGE,
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                            pad=("vehicle", "battery_capacity_kwh")),
    SolunaSensorDescription(key="vehicle_temp_inside", name="Binnentemperatuur",
                            apparaat="auto", device_class=SensorDeviceClass.TEMPERATURE,
                            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                            state_class=SensorStateClass.MEASUREMENT,
                            pad=("vehicle", "temp_in_car_c")),
    *[SolunaSensorDescription(key=f"vehicle_tire_{wiel}", name=f"Band {naam}",
                              apparaat="auto", icon="mdi:tire",
                              pad=("vehicle", f"tire_{wiel}_bar"), **BANDENSPANNING)
      for wiel, naam in (("front_left", "linksvoor"), ("front_right", "rechtsvoor"),
                         ("rear_left", "linksachter"), ("rear_right", "rechtsachter"))],
    # Wanneer de auto voor het laatst is uitgelezen. Belangrijk om te tonen: deze
    # integratie wekt de auto nooit, dus de waarden hierboven kunnen dagen oud zijn.
    SolunaSensorDescription(key="vehicle_last_update", name="Laatst uitgelezen",
                            apparaat="auto", icon="mdi:update",
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("vehicle", "last_update"), **TIJDSTIP),

    # ── Gebeurtenissen: tijdstip van de laatste keer ───────────────────────────
    # Als tijdstempel, zodat een automatisering kan reageren op "is veranderd". De
    # melding zelf en het aantal van vandaag staan in de attributen.
    SolunaSensorDescription(key="event_fuse_guard", name="Laatste ingreep zekering",
                            icon="mdi:fuse-alert", altijd=True,
                            pad=("events", "fuse_guard", "last"), **TIJDSTIP),
    SolunaSensorDescription(key="event_uncommanded_start",
                            name="Laatste laadstart zonder opdracht",
                            icon="mdi:ev-plug-type2", altijd=True,
                            pad=("events", "uncommanded_charge_start", "last"), **TIJDSTIP),
    SolunaSensorDescription(key="event_charger_command_failed",
                            name="Laatste mislukt laadcommando",
                            icon="mdi:alert-octagon", altijd=True,
                            pad=("events", "charger_command_failed", "last"), **TIJDSTIP),
    SolunaSensorDescription(key="event_pause_throttled",
                            name="Laatste geweigerde pauze",
                            icon="mdi:pause-octagon", altijd=True,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            pad=("events", "surplus_pause_throttled", "last"), **TIJDSTIP),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: SolunaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entiteiten = []
    for beschrijving in SENSOREN:
        if beschrijving.altijd:
            # Aanmaken zodra het omringende blok bestaat: een tijdstip van een gebeurtenis
            # die nog nooit is voorgekomen is leeg, maar de sensor hoort er wel te zijn.
            ouder = coordinator.waarde(*beschrijving.pad[:-1])
            if not isinstance(ouder, dict):
                continue
            entiteiten.append(SolunaSensor(coordinator, entry, beschrijving))
            continue
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
        # Ongewijzigd ten opzichte van 1.0.0: een andere unique_id zou de geschiedenis
        # van bestaande sensoren in Home Assistant loskoppelen.
        self._attr_unique_id = f"{entry.entry_id}_{beschrijving.key}"
        self._attr_device_info = apparaat_info(coordinator, entry, beschrijving.apparaat)

    @property
    def available(self) -> bool:
        return super().available and beschikbaar(
            self.coordinator, self.entity_description.meters, self.entity_description.online)

    @property
    def native_value(self):
        waarde = self.coordinator.waarde(*self.entity_description.pad)
        if self.entity_description.omzetter is not None:
            waarde = self.entity_description.omzetter(waarde)
        return waarde

    @property
    def extra_state_attributes(self) -> dict | None:
        # Gebeurtenissen: de melding en hoe vaak vandaag. Als attribuut en niet als
        # eigen sensor, anders krijg je per soort gebeurtenis twee entiteiten.
        pad = self.entity_description.pad
        if pad[0] != "events":
            return None
        blok = self.coordinator.waarde(*pad[:-1], standaard={})
        return {"melding": blok.get("last_message"), "vandaag": blok.get("today", 0)}
