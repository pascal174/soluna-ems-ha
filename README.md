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
| **Laadpaal** *(1.1.0)* | Ingesteld vermogen, storingscode, meterstand, bereikbaar, 3-fase; vandaag geladen, waarvan van het net, en de **laadkosten** |
| **Slim laden** *(1.1.0)* | Aan/uit, status, doel en voortgang (kWh), klaar-om, of het nu een goedkoop uur is |
| **Overschot-laden** *(1.1.0)* | Aan/uit, actief, vermogen; bij een Peblar ook hoe vaak hij nog mag pauzeren |
| **Auto** *(1.1.0, eigen apparaat)* | Accu (%), actieradius, kilometerstand, energie in de accu, nog te laden, capaciteit, binnentemperatuur, bandenspanning per wiel, bandenwaarschuwing, laadt, kabel aangesloten, **laatst uitgelezen** |
| **Gebeurtenissen** *(1.1.0)* | Tijdstip van de laatste ingreep van de zekeringbeveiliging, laadstart zonder opdracht, mislukt laadcommando en geweigerde pauze — met de melding en het aantal van vandaag als attribuut |
| **Meters** *(1.1.0)* | Netmeter, zonnemeter en batterij verbonden |

Entiteiten worden alleen aangemaakt als jouw installatie die waarde ook levert. Zonder batterij,
gasaansluiting of laadpaal verschijnen die dus niet — geen rijtje sensoren op "onbekend".

> Voor alles wat met *(1.1.0)* is gemarkeerd is **Soluna EMS 2.1.55 of nieuwer** nodig. Met een oudere
> EMS werkt de integratie gewoon, alleen verschijnen die entiteiten dan niet.

## De auto wordt nooit gewekt

De autogegevens zijn **de laatste uitlezing** die de EMS heeft opgeslagen. Deze integratie vraagt de auto
nooit om nieuwe gegevens, en de EMS doet dat voor Home Assistant ook niet: een uitlezing wekt de auto uit
zijn slaap en kost rijbereik. Bijwerken gebeurt alleen met de knop op de Laadpaal-pagina van de EMS.

De gegevens kunnen dus uren of dagen oud zijn. Kijk daarom naar **Laatst uitgelezen** voordat je op het
accupercentage vertrouwt, of gebruik die sensor in een automatisering.

De **positie** van de auto en het **chassisnummer** worden bewust niet doorgegeven.

## Niet beschikbaar als een meter wegvalt

Valt de netmeter, de zonnemeter of de batterij weg, dan gaan de sensoren die daarvan afhangen op **niet
beschikbaar** in plaats van de laatste waarde te blijven tonen. Huisverbruik hangt van alle drie af.
Dagtotalen en meterstanden uit de database blijven gewoon zichtbaar. Welke meter het is, zie je aan de
diagnosesensoren *Netmeter verbonden*, *Zonnemeter verbonden* en *Batterij verbonden*.

Hetzelfde geldt voor de live waarden van de laadpaal als die onbereikbaar is.

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

Sinds 1.1.0 is ook **Laadpaal meterstand** bruikbaar, als individueel apparaat. Dat is de levenslange
teller van de laadpaal zelf, geen sessieteller.

## Belasting

De integratie haalt standaard elke 10 seconden één document op. Dat kost de EMS vrijwel niets: het
endpoint serveert de laatste meting die de regellus toch al deed en leest zelf **geen hardware uit**.
Dat is bewust — de RS485-gateway van de omvormer accepteert maar één verbinding tegelijk, en extra
uitleesverkeer zou de regeling verstoren. Het interval is achteraf aan te passen via *Configureren*.
