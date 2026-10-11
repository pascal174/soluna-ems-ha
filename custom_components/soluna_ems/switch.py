"""Schakelaars: slim laden en overschot-laden aan/uit."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .bediening import SolunaBediening, heeft_laadpaal
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    if not heeft_laadpaal(c):
        return
    async_add_entities([
        SolunaSchakelaar(c, entry, "slim_laden", "Slim laden", "mdi:clock-time-four-outline",
                         ("ev_smart", "enabled"), "smart_on", "smart_off"),
        SolunaSchakelaar(c, entry, "overschot_laden", "Overschot-laden", "mdi:solar-power-variant",
                         ("ev_surplus", "enabled"), ("surplus", {"enabled": True}),
                         ("surplus", {"enabled": False})),
    ])


class SolunaSchakelaar(SolunaBediening, SwitchEntity):
    """`aan`/`uit`: een actienaam, of (actie, extra gegevens)."""

    def __init__(self, coordinator, entry, sleutel, naam, icoon, pad, aan, uit) -> None:
        super().__init__(coordinator, entry, sleutel, naam, icoon)
        self._pad, self._aan, self._uit = pad, aan, uit

    @property
    def is_on(self) -> bool | None:
        waarde = self.coordinator.waarde(*self._pad)
        return None if waarde is None else bool(waarde)

    async def _doe(self, wat) -> None:
        actie, gegevens = (wat, {}) if isinstance(wat, str) else wat
        await self.coordinator.stuur(actie, **gegevens)

    async def async_turn_on(self, **kwargs) -> None:
        await self._doe(self._aan)

    async def async_turn_off(self, **kwargs) -> None:
        # Slim laden uit stopt ook het laden, net als op het EMS-dashboard.
        await self._doe(self._uit)
