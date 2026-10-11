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
from homeassistant.exceptions import HomeAssistantError
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
        self._bedien_url = f"http://{host}:{port}/api/ha/control"
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

    async def stuur(self, actie: str, **gegevens) -> dict:
        """Stuur één bedien-actie naar de EMS en haal daarna meteen de nieuwe stand op.

        Een geweigerde actie wordt een foutmelding in Home Assistant, met de reden die de
        EMS geeft. Zonder die melding lijkt een schakelaar te reageren terwijl er niets is
        gebeurd — en springt hij bij de volgende poll stilletjes terug.
        """
        try:
            async with async_timeout.timeout(20):
                resp = await self._session.post(self._bedien_url, headers=self._headers,
                                                json={"action": actie, **gegevens})
                if resp.status == 404:
                    raise HomeAssistantError(
                        "Deze EMS kan nog niet bediend worden vanuit Home Assistant "
                        "(Soluna EMS 2.1.59 of nieuwer nodig)")
                try:
                    antwoord = await resp.json(content_type=None)
                except ValueError:
                    antwoord = {"ok": False, "error": f"onleesbaar antwoord (HTTP {resp.status})"}
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Geen verbinding met de EMS: {err}") from err
        except TimeoutError as err:
            raise HomeAssistantError("De EMS reageerde niet binnen 20 seconden") from err
        if resp.status == 401:
            raise HomeAssistantError("Token geweigerd door de EMS")
        if not (antwoord or {}).get("ok"):
            reden = (antwoord or {}).get("error") or \
                ((antwoord or {}).get("result") or {}).get("error") or f"HTTP {resp.status}"
            raise HomeAssistantError(f"De EMS weigerde '{actie}': {reden}")
        await self.async_request_refresh()
        return antwoord

    def waarde(self, *pad, standaard=None):
        """Lees een geneste waarde, bv. waarde("power", "solar_w")."""
        knoop = self.data or {}
        for sleutel in pad:
            if not isinstance(knoop, dict) or sleutel not in knoop:
                return standaard
            knoop = knoop[sleutel]
        return standaard if knoop is None else knoop
