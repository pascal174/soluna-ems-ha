"""Soluna EMS voor Home Assistant: uitlezen, en bedienen als de gebruiker dat toestaat."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from homeassistant.helpers import device_registry as dr

from .apparaat import apparaat_info
from .const import CONF_BEDIENING, CONF_TOKEN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import SolunaCoordinator

PLATFORMS = ["sensor", "binary_sensor"]
# Alleen geladen als bedienen in de opties aan staat. Staat het uit, dan bestaan deze
# entiteiten niet: een automatisering of een misklik op het dashboard kan dan niets.
BEDIEN_PLATFORMS = ["switch", "number", "select", "button", "time"]


def _platforms(entry: ConfigEntry) -> list[str]:
    return PLATFORMS + (BEDIEN_PLATFORMS if entry.options.get(CONF_BEDIENING) else [])


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SolunaCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        token=entry.data.get(CONF_TOKEN, ""),
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    # Eerste ophaal vóór het aanmaken van de entiteiten: dan weten we meteen welke
    # waarden deze installatie levert en maken we geen sensoren aan die altijd leeg zijn.
    await coordinator.async_config_entry_first_refresh()

    # Het EMS-apparaat vooraf aanmaken. De auto verwijst ernaar met `via_device_id`, en dat
    # is een registry-id: dat bestaat pas als het apparaat geregistreerd is. Zou het pas
    # ontstaan bij het toevoegen van de eerste sensor, dan kon de auto in dezelfde ronde
    # nog niet naar hem verwijzen. Bestaat het apparaat al, dan geeft dit hetzelfde terug.
    apparaat = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **apparaat_info(coordinator, entry, "ems"))
    coordinator.ems_device_id = apparaat.id

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _platforms(entry))
    entry.async_on_unload(entry.add_update_listener(_options_gewijzigd))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, _platforms(entry))
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok


async def _options_gewijzigd(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Opties aangepast (pollinterval, bedienen) → integratie opnieuw laden."""
    await hass.config_entries.async_reload(entry.entry_id)
