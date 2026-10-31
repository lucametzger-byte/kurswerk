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
