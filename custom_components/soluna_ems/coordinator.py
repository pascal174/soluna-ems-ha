"""Ophalen en verdelen van de EMS-status.

Eén coördinator haalt periodiek het complete statusdocument op; alle entiteiten lezen
daaruit. Zo blijft het bij één HTTP-verzoek per interval, ongeacht hoeveel sensoren er
aanstaan.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolunaCoordinator(DataUpdateCoordinator):
    """Haalt /api/ha/state op en houdt het resultaat bij."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, token: str,
                 scan_interval: int) -> None:
        self._session = async_get_clientsession(hass)
        self._url = f"http://{host}:{port}/api/ha/state"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.host = host
        self.port = port
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict:
        try:
            async with async_timeout.timeout(10):
                resp = await self._session.get(self._url, headers=self._headers)
                if resp.status == 401:
                    raise UpdateFailed("Token geweigerd door de EMS")
                if resp.status == 503:
                    # De regellus is nog niet gestart (EMS net herstart). Geen fout:
                    # de entiteiten worden even 'niet beschikbaar' en herstellen vanzelf.
                    raise UpdateFailed("EMS-regellus is nog niet gestart")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Geen verbinding met de EMS: {err}") from err

    def waarde(self, *pad, standaard=None):
        """Lees een geneste waarde, bv. waarde("power", "solar_w")."""
        knoop = self.data or {}
        for sleutel in pad:
            if not isinstance(knoop, dict) or sleutel not in knoop:
                return standaard
            knoop = knoop[sleutel]
        return standaard if knoop is None else knoop
