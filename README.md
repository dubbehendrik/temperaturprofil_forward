# Temperaturprofil – Vorwärtssimulation

Interaktive Streamlit-Lehrapp zur Berechnung der Erwärmung und Abkühlung eines Körpers bei vorgegebenem Wärmeübergangskoeffizienten α. Aufbau und Hochschullogo orientieren sich an [temperaturprofil](https://github.com/dubbehendrik/temperaturprofil).

## Start

Python 3.11 oder neuer, empfohlen 3.11:

```bash
pip install -r requirements.txt
streamlit run streamlit_temperaturprofil_forward_app.py
```

Für Streamlit Community Cloud: Repository `dubbehendrik/temperaturprofil_forward`, Branch `main`, Startdatei `streamlit_temperaturprofil_forward_app.py`. Das Repository allein stellt noch keine öffentlich laufende App bereit.

## Modell und Eingaben

`T(t) = T_inf - (T_inf - T0) * exp(-alpha * A * t / (m * cp))`

| Eingabe | Einheit | Standard |
|---|---|---:|
| α | W/(m² K) | 10 |
| Oberfläche A | m² | 0,1 |
| Masse m | kg | 1 |
| Spezifische Wärmekapazität cₚ | J/(kg K) | 900 |
| Anfangstemperatur T₀ | °C | 20 |
| Umgebungstemperatur T∞ | °C | 100 |
| Endzeit | s | 600 |
| Zeitschritt | s | 1 |

Die Temperatur des Körpers wird als räumlich einheitlich angenommen. Alle Parameter und die Umgebungstemperatur bleiben konstant. Strahlung, Phasenwechsel und innere Wärmequellen werden nicht separat abgebildet. Die Gültigkeit dieser Vereinfachung ist für den jeweiligen Versuch zu prüfen; gute numerische Ergebnisse allein belegen sie nicht.

Die Lösung ist analytisch. Der Zeitschritt bestimmt lediglich die Abtastung. Startzeit und exakte Endzeit sind enthalten; der letzte Schritt darf kürzer sein. Bis zu 20.001 Stützstellen je Kurve. α = 0 ergibt eine konstante Temperatur. Unphysikalische oder nicht endliche Eingaben werden abgefangen.

## Bedienung

1. Parameter direkt eingeben. Die gestrichelte Vorschau aktualisiert sich nach Übernahme einer Eingabe (Enter oder Verlassen des Feldes).
2. **Plot** übernimmt einen unveränderlichen Schnappschuss der Parameter als durchgezogene Kurve.
3. Mit **Graph behalten** wird die neue Kurve ergänzt; ohne Häkchen ersetzt sie beim nächsten Klick auf **Plot** alle bisherigen Kurven.
4. Parameterboxen sind innerhalb der Diagrammfläche neben den Achsen angeordnet, jeweils in Kurvenfarbe. Die Diagrammhöhe wächst bei vielen Kurven, damit sich die Boxen nicht überlagern.
5. Eine mit der letzten übernommenen Kurve identische Vorschau wird zur Vermeidung deckungsgleicher Linien ausgeblendet.
6. **Reset** löscht übernommene Kurven, setzt sämtliche Eingaben und Ansichtsoptionen zurück und zeigt die Standardvorschau.

Zoom, Verschieben, numerische Achsengrenzen, Sekunden/Minuten und veränderliche Diagrammhöhe sind verfügbar. Über „Diagramm über gesamte Breite“ lässt sich der Plot unterhalb des Parameterbereichs größer darstellen. „Ansicht zurücksetzen“ verändert keine Modellparameter und keine gespeicherten Kurven.

## Export

Nur übernommene Kurven werden exportiert, niemals die Vorschau:

- CSV: Semikolon, Dezimalkomma, UTF-8 mit BOM; Zeit in Sekunden, Temperatur in °C, Parameter je Datenzeile.
- Excel: Tabellen „Temperaturverläufe“, „Parameter“ und „Einheiten“. Unterschiedliche Zeitraster werden im langen Tabellenformat erhalten.
- PNG und SVG: alle übernommenen Kurven mit farbigen Parameterboxen. Das Bild verwendet die eingestellte Zeiteinheit und numerischen Achsengrenzen. Interaktiver Maus-Zoom wird nicht an den Server zurückgegeben und daher nicht in den Export übernommen.

PNG/SVG werden mit Matplotlib erstellt; Chrome/Kaleido sind nicht erforderlich. Eingaben und Kurven existieren nur in der jeweiligen Sitzung. Kein Excel-Import, keine Datenbank, keine Anmeldung und keine externen Datenabrufe in der App.

## Struktur und Prüfung

Das Hauptskript enthält Modellfunktionen, Diagramm- und Exportfunktionen und die Streamlit-Oberfläche. Der `main()`-Einstieg erlaubt das isolierte Testen der Funktionen. Das Hochschullogo wird lokal geladen.

```bash
python -m unittest discover -s tests -v
```

Tests prüfen analytische Referenzfälle, Abkühlung, α = 0, Endzeit, Eingabevalidierung, Datenausgabe sowie die Streamlit-Interaktion für Behalten, Ersetzen und Reset.

## Verwendung

Demonstrations- und Lehrzwecke. Eine kommerzielle Verwendung ist nicht gestattet. Hochschullogo aus dem bestehenden Repository unverändert übernommen. Kontakt: Prof. Dr.-Ing. Hendrik Dubbe, hendrik.dubbe@hs-esslingen.de.
