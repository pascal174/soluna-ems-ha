# Changelog — Soluna EMS Home Assistant-integratie

## 1.2.0 — 2026-10-11

Vereist voor het bedienen: **Soluna EMS 2.1.59 of nieuwer**. Uitlezen werkt met elke EMS-versie zoals
voorheen.

- **Bedienen vanuit Home Assistant, standaard uit.** Nieuwe optie *Bediening toestaan*. Staat die uit,
  dan worden de bedien-entiteiten niet aangemaakt; uitzetten haalt ze weer weg.
- **Laadpaal**: schuif *Laadvermogen*, knop *Laden stoppen*, schakelaar *Overschot-laden*.
- **Slim laden**: schakelaar, en *hoeveel* (kWh), *laadvermogen* (kW) en *klaar om* (tijd). Bijstellen
  tijdens een sessie houdt de voortgang vast.
- **EMS-sturing**: keuzelijsten *Regelmodus*, *Handmatige strategie* en *Optimizer*.
- **Thuisaccu**: keuzelijst *Accu-opdracht* (stil/laden/ontladen) en schuif *Accu-vermogen*.
- Alles loopt via de EMS (`POST /api/ha/control`) en dezelfde controles als het dashboard. Een
  geweigerde actie wordt een foutmelding met de reden, in plaats van een schakelaar die stilletjes
  terugspringt. Niets wekt de auto.

## 1.1.0 — 2026-10-09

Vereist voor de nieuwe entiteiten: **Soluna EMS 2.1.55 of nieuwer**. Met een oudere EMS werkt deze
versie gewoon; de nieuwe entiteiten verschijnen dan niet.

- **Laadpaal**: ingesteld vermogen, storingscode, meterstand (bruikbaar in het energiedashboard),
  bereikbaar, 3-fase, en vandaag: geladen kWh, waarvan van het net, en de laadkosten.
- **Slim laden**: aan/uit, status, doel en voortgang, klaar-om, en of het nu een goedkoop uur is.
- **Overschot-laden**: aan/uit, actief, vermogen; bij een Peblar-laadpaal ook hoe vaak hij de komende
  tien minuten nog mag pauzeren.
- **Auto**, als eigen apparaat gekoppeld aan de EMS: accu, actieradius, kilometerstand, energie in de
  accu, nog te laden, capaciteit, binnentemperatuur, bandenspanning per wiel, bandenwaarschuwing,
  laadt, kabel aangesloten, en wanneer hij voor het laatst is uitgelezen.
  - De auto wordt hiervoor **nooit gewekt**. Het zijn de gegevens van de laatste uitlezing in de EMS;
    bijwerken gaat alleen met de knop op de Laadpaal-pagina. Daarom de sensor *Laatst uitgelezen*.
  - Positie en chassisnummer worden niet doorgegeven.
- **Gebeurtenissen** als tijdstempel, zodat een automatisering kan reageren: laatste ingreep van de
  zekeringbeveiliging, laadstart zonder opdracht, mislukt laadcommando, geweigerde pauze. De melding
  en het aantal van vandaag staan in de attributen.
- **Meters**: netmeter, zonnemeter en batterij verbonden.
- **Sensoren gaan op *niet beschikbaar* als hun meter wegvalt**, in plaats van de laatste waarde te
  blijven tonen. Huisverbruik hangt van alle drie af. Dagtotalen uit de database blijven zichtbaar.
- **`via_device_id` in plaats van `via_device`.** Home Assistant 2026.8 maakte `via_device` verouderd;
  in 2027.8 stopt het. Het EMS-apparaat wordt nu vooraf aangemaakt zodat de auto er met zijn
  registry-id naar kan verwijzen. Er wordt getest op het bestáán van het nieuwe veld in `DeviceInfo`,
  niet op een versienummer, zodat oudere Home Assistant-versies het oude veld blijven krijgen.
  Geverifieerd op een echte Home Assistant 2026.9.3: de verouderingsmelding is weg en de auto staat in
  het register als "Auto via Soluna EMS", gekoppeld aan de EMS.
- De link naar de EMS in de apparaatinfo gebruikt de ingestelde poort in plaats van vast 5555.
- Alle entiteiten van 1.0.0 behouden hun sleutel, dus hun geschiedenis blijft.

## 1.0.0 — 2026-08-04

Eerste versie: alleen-lezen integratie voor vermogens, batterij, sturing, prijzen, meterstanden,
dagtotalen, zonverwachting en het net per fase.
