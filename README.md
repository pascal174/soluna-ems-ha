# Soluna EMS — Home Assistant integratie

Leest je [Soluna EMS](https://github.com/pascal174/solana) uit in Home Assistant. **Alleen lezen**: de
integratie kan niets aan je installatie veranderen. Er zitten geen schakelaars, knoppen of services in.

## Wat je krijgt

| Groep | Entiteiten |
|---|---|
| **Vermogens** | Zon, net, batterij, huisverbruik, laadpaal (W) |
| **Batterij** | Laadtoestand (%), status, vermogen, accuspanning/-stroom, accutemperatuur, laadcycli, temperatuur omvormer en koellichaam |
| **Sturing** | Strategie, sturingsmodus (automatisch/handmatig), optimizer-bron |
| **Prijzen** | Prijs nu, laagste/hoogste/gemiddelde vandaag (€/kWh) |
| **Meterstanden** | Net afgenomen/teruggeleverd, zonopbrengst, gas — oplopende tellers, geschikt voor het **energiedashboard** |
| **Dagtotalen** | Zon, verbruik, afname, teruglevering, batterij geladen/ontladen, kosten en opbrengst |
| **Verwachting** | Zonverwachting vandaag en morgen (kWh) |
| **Net per fase** | Spanning, stroom en vermogen op L1/L2/L3, actief tarief |
| **Aan/uit** | Laadpaal aangesloten, auto laadt, batterij op een grens, omvormerstoring |

Entiteiten worden alleen aangemaakt als jouw installatie die waarde ook levert. Zonder batterij,
gasaansluiting of laadpaal verschijnen die dus niet — geen rijtje sensoren op "onbekend".

## Installatie via HACS

1. HACS → Integraties → ⋮ → **Aangepaste repositories**
2. Voeg deze repository toe, categorie **Integration**
3. Zoek op *Soluna EMS*, installeer, herstart Home Assistant
4. Instellingen → Apparaten & diensten → **Integratie toevoegen** → *Soluna EMS*
5. Vul het IP-adres van je EMS in (poort 5555)

Handmatig kan ook: kopieer `custom_components/soluna_ems` naar je Home Assistant-configuratiemap.

## Token

Standaard is er geen token nodig — de EMS draait op je eigen netwerk, net als de rest van je apparaten.
Ontsluit je de EMS buiten je LAN, zet dan `ha_api_token` in de EMS-instellingen; daarna is het token
verplicht en vul je het in bij het toevoegen van de integratie.

## Energiedashboard

De vier oplopende tellers zijn direct bruikbaar:

- **Net afgenomen totaal** → Netstroom verbruik
- **Net teruggeleverd totaal** → Teruglevering aan het net
- **Zonopbrengst totaal** → Zonnepanelen
- **Gasverbruik totaal** → Gas

Deze komen rechtstreeks uit je slimme meter en de kWh-meter van de panelen, dus ze lopen gelijk met de
standen op de meters zelf.

## Belasting

De integratie haalt standaard elke 10 seconden één document op. Dat kost de EMS vrijwel niets: het
endpoint serveert de laatste meting die de regellus toch al deed en leest zelf **geen hardware uit**.
Dat is bewust — de RS485-gateway van de omvormer accepteert maar één verbinding tegelijk, en extra
uitleesverkeer zou de regeling verstoren. Het interval is achteraf aan te passen via *Configureren*.
