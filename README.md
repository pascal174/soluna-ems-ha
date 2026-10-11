# Soluna EMS — Home Assistant integratie

Leest je [Soluna EMS](https://github.com/pascal174/solana) uit in Home Assistant, en kan hem bedienen
als je dat toestaat. **Standaard alleen lezen**: bedienen zet je zelf aan in de opties (zie
[Bedienen](#bedienen)).

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

## Bedienen

*(1.2.0, vereist Soluna EMS 2.1.59 of nieuwer)*

Standaard staat bedienen **uit**: dan bestaan de bedien-entiteiten niet, en kan een automatisering of
een misklik op het dashboard niets aan je installatie veranderen. Aanzetten: Instellingen → Apparaten &
diensten → *Soluna EMS* → **Configureren** → **Bediening toestaan**. Uitzetten haalt ze weer weg.

| Groep | Entiteit | Wat het doet |
|---|---|---|
| **Laadpaal** | *Laadvermogen* (schuif, kW) | Handmatig laadvermogen; 0 = pauzeren. Zet slim laden uit, net als op het dashboard. Op een 3-fase laadpaal is ±4,1 kW het minimum (6 A per fase); daaronder pauzeert hij. |
| | *Laden stoppen* (knop) | Pauzeert het laden en zet slim laden uit. |
| | *Overschot-laden* (schakelaar) | Laden op zonne-overschot aan/uit. |
| **Slim laden** | *Slim laden* (schakelaar) | Aan met de instellingen hieronder; uit stopt ook het laden. |
| | *Slim laden: hoeveel* (kWh), *laadvermogen* (kW), *klaar om* (tijd) | De instellingen. Bijstellen tijdens een sessie houdt de voortgang vast: van 30 naar 35 kWh betekent er nog 5 bij, niet 35 opnieuw. |
| **EMS-sturing** | *Regelmodus* | Automatisch (de optimizer stuurt) of handmatig. Terug naar automatisch wist een vaste accu-opdracht of geforceerde strategie. |
| | *Handmatige strategie* | Een strategie forceren (balanceren, opladen, ontladen, alleen injectie, piekscheren); zet de modus op handmatig. |
| | *Optimizer* | Regels of AI. |
| **Thuisaccu** | *Accu-opdracht* | Stil, laden of ontladen met een vast vermogen; zet de modus op handmatig. |
| | *Accu-vermogen* (schuif, W) | Het vermogen voor die opdracht. Loopt er een laad- of ontlaadopdracht, dan gaat een nieuw vermogen meteen mee. |

Alle acties gaan naar `POST /api/ha/control` op de EMS en lopen daar via **hetzelfde endpoint als een
klik op het EMS-dashboard**. De grenzen worden dus door de EMS bewaakt, niet door deze integratie: het
maximum van de laadpaal, de SoC-grenzen en maximale vermogens van de accu, de zekeringbeveiliging, het
beslissingslogboek. Weigert de EMS iets, dan krijg je in Home Assistant een foutmelding met de reden.

Wat er bewust níet bij zit: iets wat de auto wekt of uitleest, en het wijzigen van apparaten of andere
instellingen van de EMS.

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
