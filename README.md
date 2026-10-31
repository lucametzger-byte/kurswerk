# Kurswerk Terminal

Börsenterminal im Bloomberg-Stil mit Analyse-Bot, Monte-Carlo-Prognose und Spielgeld-Depot.

**Zwei Modi** (Schalter oben rechts):
- **Live**: echte Kurse und News von Yahoo Finance, alle ~10 Minuten aktualisiert (Börsenkurse teils 15 Min. verzögert). Gehandelt wird mit Spielgeld.
- **Simulation**: simulierter Markt mit rund 140 Titeln (Schweiz, USA, Europa, Asien, Krypto, Rohstoffe, Devisen). Branchen bewegen sich gemeinsam, es gibt Quartalszahlen, Branchen-News, Crashs und Rallys. Tempo: Pause, 1× (ein Handelstag = 2 Minuten), 5× oder 20×.

Jeder Modus hat sein eigenes Depot mit CHF 100’000 Startkapital. Gespeichert wird im Browser.

## Master-Bot

Der Master-Bot handelt rund um die Uhr mit CHF 100’000 Spielgeld, auch wenn die Website geschlossen ist. Er läuft bei jedem Workflow-Lauf (`scripts/bot.mjs`) nach der Strategie **Signal + Kern**, die im Backtest über verschiedene Zeitfenster am beständigsten war:

- Kern: 50 % im SMI, solange der SMI über seiner 50-Tage-Linie liegt.
- Einzeltitel bei Signal ab +30 an zwei Tagen in Folge, nur bei Aufwärtstrend im Heimmarkt.
- Positionsgrösse nach Schwankung, höchstens 15 % pro Titel, Trailing-Stop bei 3 ATR.

Sein Stand liegt als `bot.json` im Branch `bot-state`. Zum Neustart mit frischem Spielgeld diesen Branch löschen.

Die Regeln stehen einmal in `bt.js` und werden vom Backtest, vom Browser-Autopiloten und vom Master-Bot gemeinsam benutzt.

## So funktioniert es

- `scripts/fetch_data.py` holt mit yfinance zwei Jahre Tageskerzen, USD/CHF und aktuelle News.
- `.github/workflows/update.yml` läuft alle 10 Minuten, schreibt `data/market.json` und veröffentlicht alles auf GitHub Pages. Kurse werden nicht committet; nur der Master-Bot speichert etwa stündlich seinen Stand im Branch `bot-state`.
- `index.html` ist das Terminal: Chart, Indikatoren, Bot, Depot, Autopilot.

## Manuell aktualisieren

Gehe auf **Actions → Kurse aktualisieren → Run workflow**.

## Hinweis

GitHub pausiert geplante Workflows in öffentlichen Repos nach 60 Tagen ohne Aktivität. Falls die Kurse stehen bleiben, starte den Workflow einmal manuell oder pushe eine kleine Änderung.

Lernprojekt. Keine Anlageberatung.
