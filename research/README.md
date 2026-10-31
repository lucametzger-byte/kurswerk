# Analyse-Modell trainieren und prüfen

Lokal mit Python 3.11+ (`pip install numpy pandas scikit-learn`) und Node 18+.

1. Kurshistorie holen: im Branch `history-data` liegt `history.json.gz` (wöchentlich vom Workflow *Kurshistorie holen* erneuert).
   `git fetch origin history-data && git show origin/history-data:history.json.gz > research/history.json.gz`
2. Im Ordner `research/`:
   - `python3 panel.py` – Messpunkte bauen (jeder 5. Handelstag, Faktoren + Rendite der nächsten 20 Tage)
   - `python3 wf.py` – Walk-Forward-Vergleich der Modelle (jedes Jahr nur mit den Daten davor gelernt)
   - `python3 export.py` – finales Modell + Trefferquoten nach `model.json`; den Inhalt in `bt.js` bei `const MODEL=` einsetzen
   - `python3 wfw.py && node e2e.js` – Handelsstrategien über 2000–heute nachspielen. Die Bots nutzen das Trendsignal; für den Vergleich mit dem Prognose-Score in `bt.js` bei `run()`/`runRot()` `trendScore` vorübergehend durch `score` ersetzen.

Messgrössen: **IC** = Rang-Korrelation zwischen Score und späterer Rendite pro Stichtag (0 = Zufall, negativ = falsche Richtung).
Profi-Modelle liegen typischerweise bei 0,02–0,05.

Ergebnis Oktober 2026 (Testjahre 2000–2026, 142 Aktien):
- bisheriger Score: IC −0,016 (hohe Scores liefen danach schlechter)
- neues Modell: IC +0,009, in allen drei Jahrzehnten und in CH wie USA positiv
- Handelsstrategien: mit dem neuen Score nicht robust besser, darum handeln alle Bots weiter mit dem Trendsignal.

Bekannte Grenzen: nur heute existierende Firmen (Survivorship-Bias), keine historischen News, Kurse in Lokalwährung.

## Kronos-Test (Oktober 2026)

Kronos-small (Foundation-Modell für Kerzencharts, vortrainiert auf 12 Mrd. Kerzen) hat für 142 Aktien an 32 Stichtagen
die nächsten 20 Handelstage vorhergesagt, nur zwischen Juli 2025 und September 2026, also nach dem Ende seiner
Trainingsdaten (Juni 2025). Skripte: `kronos_test.py` (läuft im Workflow «Kronos testen», nur manuell), `kronos_eval.py`.

| Signal | IC | Stichtage mit IC > 0 |
|---|---|---|
| Trendsignal (alt) | +0,018 | 66 % |
| Analyse-Modell | +0,003 | 50 % |
| Kronos | −0,012 | 41 % |
| Analyse-Modell + Kronos | −0,017 | 50 % |

- Kronos trifft die Richtung nicht: Korrelation mit der echten 20-Tage-Rendite +0,005, bei seinen stärksten Prognosen 49 % Treffer.
- Es sagt zu oft «fällt» (69 % der Fälle, tatsächlich stieg der Kurs in 55 %) und überschätzt die Bewegung (Ø 10,7 % statt 6,5 %).
- Mit dem Analyse-Modell kombiniert wird es schlechter. **Darum nicht eingebaut.**
- Vorbehalt: 15 Monate sind kurz, auch das Analyse-Modell ist darin nicht signifikant. Kronos zeigt aber kein Anzeichen eines Vorteils.
