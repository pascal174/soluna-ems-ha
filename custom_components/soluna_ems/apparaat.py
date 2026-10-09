"""Gedeeld door de sensoren en de binaire sensoren: apparaat en beschikbaarheid."""
from __future__ import annotations

from .const import DOMAIN

# Home Assistant 2026.8 verving `via_device` (de identificatie van het moederapparaat) door
# `via_device_id` (zijn id in het register); de oude vorm stopt in 2027.8. Deze integratie
# belooft te werken vanaf 2024.1, dus er wordt getest op het bestáán van het nieuwe veld
# in plaats van op een versienummer. Ontbreekt het, dan blijft de oude vorm in gebruik.
try:
    from homeassistant.helpers.device_registry import DeviceInfo
    _VIA_DEVICE_ID = "via_device_id" in getattr(DeviceInfo, "__annotations__", {})
except ImportError:  # pragma: no cover
    _VIA_DEVICE_ID = False


def apparaat_info(coordinator, entry, soort: str = "ems") -> dict:
    """Het apparaat waaronder een entiteit valt.

    De auto krijgt een eigen apparaat, gekoppeld aan de EMS. Zo staan accu, actieradius en
    bandenspanning bij elkaar, los van de tientallen EMS-sensoren — en is in één oogopslag
    te zien dat ze via de EMS binnenkomen en niet rechtstreeks van de auto.
    """
    ems = (DOMAIN, entry.entry_id)
    if soort == "auto":
        label = coordinator.waarde("vehicle", "label") or "Auto"
        info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_vehicle")},
            "name": label,
            "model": "Auto via Soluna EMS",
        }
        via_id = getattr(coordinator, "ems_device_id", None)
        if _VIA_DEVICE_ID and via_id:
            info["via_device_id"] = via_id
        else:
            info["via_device"] = ems
        return info
    return {
        "identifiers": {ems},
        "name": entry.title,
        "manufacturer": "Soluna",
        "model": "Soluna EMS",
        "configuration_url": f"http://{coordinator.host}:{coordinator.port}/",
    }


def beschikbaar(coordinator, meters: tuple[str, ...] = (), online: tuple[str, ...] | None = None) -> bool:
    """Is deze waarde nu te vertrouwen?

    Drie lagen, van grof naar fijn:

    * De EMS zelf: is de laatste momentopname vers genoeg (`available`)?
    * De meetgroep: valt de zonnemeter, de netmeter of de batterij weg, dan meldt de EMS
      dat in `meters`. Zonder deze controle bleef Home Assistant de laatste waarde tonen —
      bij de zekeringuitval van 7 oktober 2026 stond de batterij een uur lang op het
      vermogen van vlak voor de storing.
    * Een apparaat met een eigen bereikbaarheid, zoals de laadpaal (`online`).

    Een EMS van vóór 2.1.5 kent `meters` niet; dan geldt de groep als in orde, zodat een
    oudere EMS niet ineens alles op 'niet beschikbaar' zet.
    """
    if not coordinator.waarde("available", standaard=False):
        return False
    for groep in meters:
        if coordinator.waarde("meters", groep, "ok", standaard=True) is False:
            return False
    if online and coordinator.waarde(*online, standaard=True) is False:
        return False
    return True
