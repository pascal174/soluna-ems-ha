"""Keuzelijsten: regelmodus, handmatige strategie, optimizer en de accu-opdracht."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity

from .bediening import SolunaBediening, heeft_accu
from .const import DOMAIN

MODI = {"auto": "Automatisch", "manual": "Handmatig"}
OPTIMIZERS = {"rule": "Regels", "ai": "AI"}
ACCU = {"idle": "Stil", "charge": "Laden", "discharge": "Ontladen"}


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    entiteiten = [
        SolunaModus(c, entry, "regelmodus", "Regelmodus", "mdi:auto-mode"),
        SolunaOptimizer(c, entry, "optimizer", "Optimizer", "mdi:brain"),
    ]
    if heeft_accu(c):
        entiteiten += [
            SolunaStrategie(c, entry, "strategie", "Handmatige strategie", "mdi:strategy"),
            SolunaAccuOpdracht(c, entry, "accu_opdracht", "Accu-opdracht", "mdi:home-battery"),
        ]
    async_add_entities(entiteiten)


class _Keuze(SolunaBediening, SelectEntity):
    """Keuzelijst met vaste labels; `_labels` = {EMS-waarde: label}."""
    _labels: dict[str, str] = {}

    @property
    def options(self) -> list[str]:
        return list(self._labels.values())

    def _label(self, waarde) -> str | None:
        return self._labels.get(waarde) if waarde else None

    def _waarde(self, label: str) -> str:
        return next(k for k, v in self._labels.items() if v == label)


class SolunaModus(_Keuze):
    _labels = MODI

    @property
    def current_option(self):
        return self._label(self.coordinator.waarde("mode", "control_mode"))

    async def async_select_option(self, option: str) -> None:
        # Terug naar automatisch wist ook een vaste accu-opdracht en een geforceerde
        # strategie; dat doet de EMS zelf.
        await self.coordinator.stuur("mode", mode=self._waarde(option))


class SolunaOptimizer(_Keuze):
    _labels = OPTIMIZERS

    @property
    def current_option(self):
        return self._label(self.coordinator.waarde("mode", "optimizer_source"))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.stuur("optimizer_source", source=self._waarde(option))


class SolunaStrategie(_Keuze):
    """Een strategie forceren zet de EMS op handmatig, net als op het dashboard."""

    @property
    def _labels(self) -> dict[str, str]:
        return self.coordinator.waarde("control", "strategies", standaard={}) or {}

    @property
    def current_option(self):
        if self.coordinator.waarde("mode", "control_mode") != "manual":
            return None
        return self._label(self.coordinator.waarde("control", "manual_strategy"))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.stuur("strategy", strategy=self._waarde(option))


class SolunaAccuOpdracht(_Keuze):
    """Vaste opdracht aan de thuisaccu, met het vermogen van de schuif 'Accu-vermogen'.

    Zet de EMS op handmatig. Terug naar de optimizer gaat via 'Regelmodus' →
    Automatisch. De SoC-grenzen en maximale vermogens van de EMS blijven gelden.
    """
    _labels = ACCU

    @property
    def current_option(self):
        if self.coordinator.waarde("mode", "control_mode") != "manual":
            return None
        return self._label(self.coordinator.waarde("mode", "manual_command") or None)

    async def async_select_option(self, option: str) -> None:
        opdracht = self._waarde(option)
        vermogen = 0
        if opdracht != "idle":
            vermogen = int(getattr(self.coordinator, "accu_vermogen_w", None) or 1000)
        await self.coordinator.stuur("battery", command=opdracht, power_w=vermogen)
