"""Tijd: wanneer de auto klaar moet zijn bij slim laden."""
from __future__ import annotations

from datetime import time as dtime

from homeassistant.components.time import TimeEntity

from .bediening import SolunaBediening, heeft_laadpaal
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    if heeft_laadpaal(c):
        async_add_entities([SolunaKlaarTijd(c, entry, "slim_laden_klaar", "Slim laden: klaar om",
                                            "mdi:clock-end")])


class SolunaKlaarTijd(SolunaBediening, TimeEntity):
    @property
    def native_value(self) -> dtime | None:
        tekst = self.coordinator.waarde("ev_smart", "ready_time")
        try:
            hh, mm = (int(x) for x in str(tekst).split(":")[:2])
            return dtime(hh, mm)
        except (TypeError, ValueError):
            return None

    async def async_set_value(self, value: dtime) -> None:
        # Staat slim laden aan, dan verschuift de deadline mee; de voortgang blijft staan.
        await self.coordinator.stuur("smart_settings", ready_time=value.strftime("%H:%M"))
