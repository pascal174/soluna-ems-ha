"""Constanten voor de Soluna EMS-integratie."""
DOMAIN = "soluna_ems"

CONF_TOKEN = "token"
# Mag Home Assistant de EMS bedienen? Standaard niet: pas als de gebruiker het in de
# opties aanzet, worden de bedien-entiteiten aangemaakt.
CONF_BEDIENING = "allow_control"

DEFAULT_PORT = 5555
DEFAULT_SCAN_INTERVAL = 10   # seconden

# De EMS-regellus draait op 1s en cachet de laatste meting; 10s pollen geeft een vlot
# dashboard zonder de EMS of de Modbus-bus te belasten (het endpoint leest zelf geen
# hardware uit).
