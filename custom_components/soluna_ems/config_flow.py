"""Configuratiestap: IP-adres, poort en een optioneel token."""
from __future__ import annotations

import aiohttp
import async_timeout
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN


async def _controleer(hass, host: str, port: int, token: str) -> dict:
    """Probeer de EMS te bereiken en haal de identificatie op."""
    sessie = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with async_timeout.timeout(10):
        resp = await sessie.get(f"http://{host}:{port}/api/ha/info", headers=headers)
        if resp.status == 401:
            raise InvalidAuth
        resp.raise_for_status()
        return await resp.json()


class SolunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            token = (user_input.get(CONF_TOKEN) or "").strip()
            try:
                info = await _controleer(self.hass, host, port, token)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                # Eén EMS per host: voorkomt dubbele entiteiten bij opnieuw toevoegen.
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info.get("name", "Soluna EMS"),
                    data={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token},
                )

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional(CONF_TOKEN, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolunaOptionsFlow(config_entry)


class SolunaOptionsFlow(config_entries.OptionsFlow):
    """Alleen het pollinterval is achteraf instelbaar."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        huidig = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=huidig): vol.All(int, vol.Range(min=5, max=300)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)


class InvalidAuth(Exception):
    """Het token werd geweigerd."""
