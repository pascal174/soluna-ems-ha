"""Knop: laden stoppen."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .bediening import SolunaBediening, heeft_laadpaal
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    if heeft_laadpaal(c):
        async_add_entities([SolunaStopKnop(c, entry, "laden_stoppen", "Laden stoppen",
                                           "mdi:ev-plug-type2")])


class SolunaStopKnop(SolunaBediening, ButtonEntity):
    async def async_press(self) -> None:
        # Zet ook slim laden uit, net als de stopknop op het EMS-dashboard: anders start
        # het in het volgende goedkope uur gewoon weer.
        await self.coordinator.stuur("charger_stop")
