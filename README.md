# Kurswerk Terminal

Börsenterminal im Bloomberg-Stil mit Analyse-Bot, Monte-Carlo-Prognose und Spielgeld-Depot.

**Zwei Modi** (Schalter oben rechts):
- **Live**: echte Kurse und News von Yahoo Finance, alle ~10 Minuten aktualisiert (Börsenkurse teils 15 Min. verzögert). Gehandelt wird mit Spielgeld.
  - **Echtzeit für Krypto**: Bitcoin, Ethereum und Solana kommen direkt im Browser live von Binance (WebSocket, ohne Anmeldung, 24/7).
  - **Echtzeit für US-Aktien**: mit einem kostenlosen API-Key von [Finnhub](https://finnhub.io/register). Oben auf **Echtzeit einrichten** klicken und den Key eintragen. Er wird nur im Browser gespeichert, nie im Repo.
  - Jeder Titel zeigt seinen Status: **Live**, **Verzögert** oder **Börse zu**. Bei geschlossener Börse handeln weder du noch der Autopilot noch der Master-Bot diesen Titel, damit nie zu alten Kursen gehandelt wird. Feiertage sind nicht berücksichtigt.
- **Simulation**: simulierter Markt mit rund 140 Titeln (Schweiz, USA, Europa, Asien, Krypto, Rohstoffe, Devisen). Branchen bewegen sich gemeinsam, es gibt Quartalszahlen, Branchen-News, Crashs und Rallys. Tempo: Pause, 1× (ein Handelstag = 2 Minuten), 5× oder 20×.

Jeder Modus hat sein eigenes Depot mit CHF 100’000 Startkapital. Gespeichert wird im Browser.

## Analyse-Bot

Der Score im Analyse-Panel ist eine **Prognose für die nächsten 20 Handelstage**. Seine Gewichte wurden auf Kursen ab 1991 von 142 Aktien aus der Schweiz, den USA und Europa gelernt, im Walk-Forward-Verfahren: Für jedes Testjahr lernt das Modell nur mit den Daten davor.

- Faktoren: Kurzfrist-Technik (Trend, Momentum, MACD, RSI, Bollinger), Momentum 12 Monate, Langfristtrend, Schwankung, Marktphase des Heimmarkts und ein kleiner News-Zuschlag.
- Statt einer geschätzten «Modell-Sicherheit» zeigt das Panel, wie oft der Kurs bei einem solchen Score historisch tatsächlich gestiegen ist.
- Der bisherige Score lag über 20 Tage im Schnitt sogar falsch herum (hohe Scores liefen danach schlechter). Das neue Modell liegt richtig, der Vorsprung ist aber klein.
- Autopilot und Master-Bot handeln weiter mit dem **Trendsignal** (der bisherigen Formel), weil ihre Regeln damit im Backtest 2000–2026 besser liefen. Das Panel zeigt beide Werte.

Training und Prüfung: Ordner `research/`. Die Kurshistorie holt der Workflow «Kurshistorie holen» wöchentlich in den Branch `history-data`.

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
