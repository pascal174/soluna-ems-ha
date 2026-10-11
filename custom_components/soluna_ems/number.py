"""Schuiven: laadvermogen, de doelen van slim laden en het vermogen van de thuisaccu."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import UnitOfEnergy, UnitOfPower

from .bediening import SolunaBediening, heeft_accu, heeft_laadpaal
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    entiteiten = []
    if heeft_laadpaal(c):
        entiteiten += [
            SolunaLaadvermogen(c, entry, "laadvermogen", "Laadvermogen", "mdi:ev-station"),
            SolunaSlimInstelling(c, entry, "slim_laden_kwh", "Slim laden: hoeveel", "mdi:battery-plus",
                                 "target_kwh", "kwh", UnitOfEnergy.KILO_WATT_HOUR, 1, 100, 1),
            SolunaSlimInstelling(c, entry, "slim_laden_vermogen", "Slim laden: laadvermogen",
                                 "mdi:flash", "power_kw", "power_kw", UnitOfPower.KILO_WATT, 1.4, None, 0.1),
        ]
    if heeft_accu(c):
        entiteiten.append(SolunaAccuVermogen(c, entry, "accu_vermogen", "Accu-vermogen",
                                             "mdi:battery-charging"))
    async_add_entities(entiteiten)


def _paal_max(coordinator) -> float:
    return float(coordinator.waarde("control", "charger_max_kw", standaard=11.0) or 11.0)


class SolunaLaadvermogen(SolunaBediening, NumberEntity):
    """Handmatig laadvermogen. Zet slim laden uit (handbediening wint), net als op het dashboard.

    0 = pauzeren. Op een 3-fase laadpaal is het laagste laadvermogen ±4,1 kW (6 A per fase);
    daaronder pauzeert de paal.
    """
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_native_min_value = 0.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER

    @property
    def native_max_value(self) -> float:
        return _paal_max(self.coordinator)

    @property
    def native_value(self) -> float | None:
        # Wat de laadpaal bevestigt, niet wat er ooit gevraagd is.
        return self.coordinator.waarde("ev", "confirmed_kw")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.stuur("charger_power", kw=round(float(value), 2))


class SolunaSlimInstelling(SolunaBediening, NumberEntity):
    """Doel of vermogen van slim laden. Bijstellen tijdens een sessie houdt de voortgang."""
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, sleutel, naam, icoon, veld, actieveld, eenheid,
                 minimum, maximum, stap) -> None:
        super().__init__(coordinator, entry, sleutel, naam, icoon)
        self._veld, self._actieveld, self._max = veld, actieveld, maximum
        self._attr_native_unit_of_measurement = eenheid
        self._attr_native_min_value = minimum
        self._attr_native_step = stap

    @property
    def native_max_value(self) -> float:
        return float(self._max) if self._max is not None else _paal_max(self.coordinator)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.waarde("ev_smart", self._veld)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.stuur("smart_settings", **{self._actieveld: float(value)})


class SolunaAccuVermogen(SolunaBediening, RestoreNumber):
    """Vermogen voor de accu-opdracht. Zelf geen opdracht: dat doet 'Accu-opdracht'.

    Loopt er al een vaste laad- of ontlaadopdracht, dan gaat het nieuwe vermogen meteen
    mee. Anders wordt het onthouden voor de volgende keer dat je 'Laden' of 'Ontladen' kiest.
    """
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 0
    _attr_native_step = 50
    _attr_mode = NumberMode.SLIDER

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        laatste = await self.async_get_last_number_data()
        lopend = self.coordinator.waarde("mode", "manual_command_w")
        waarde = lopend or (laatste.native_value if laatste else None) or 1000
        self.coordinator.accu_vermogen_w = float(waarde)

    @property
    def native_max_value(self) -> float:
        return float(max(self.coordinator.waarde("control", "battery_max_charge_w", standaard=0) or 0,
                         self.coordinator.waarde("control", "battery_max_discharge_w", standaard=0) or 0)
                     or 5000)

    @property
    def native_value(self) -> float | None:
        # Loopt er een vaste opdracht (ook een van het dashboard), dan is dát het vermogen.
        if self.coordinator.waarde("mode", "control_mode") == "manual" and \
                self.coordinator.waarde("mode", "manual_command") in ("charge", "discharge"):
            return self.coordinator.waarde("mode", "manual_command_w")
        return getattr(self.coordinator, "accu_vermogen_w", None)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.accu_vermogen_w = float(value)
        opdracht = self.coordinator.waarde("mode", "manual_command")
        if self.coordinator.waarde("mode", "control_mode") == "manual" and opdracht in ("charge", "discharge"):
            await self.coordinator.stuur("battery", command=opdracht, power_w=int(value))
        else:
            self.async_write_ha_state()
