# Kurswerk Terminal

Börsenterminal im Bloomberg-Stil mit Analyse-Bot, Monte-Carlo-Prognose und Spielgeld-Depot.

**Zwei Modi** (Schalter oben rechts):
- **Live**: echte Kurse und News von Yahoo Finance, alle ~10 Minuten aktualisiert (Börsenkurse teils 15 Min. verzögert). Gehandelt wird mit Spielgeld.
- **Simulation**: simulierter Markt, der rund um die Uhr läuft. Ein Handelstag dauert 2 Minuten.

Jeder Modus hat sein eigenes Depot mit CHF 100’000 Startkapital. Gespeichert wird im Browser.

## So funktioniert es

- `scripts/fetch_data.py` holt mit yfinance ein Jahr Tageskerzen, USD/CHF und aktuelle News.
- `.github/workflows/update.yml` läuft alle 10 Minuten, schreibt `data/market.json` und veröffentlicht alles auf GitHub Pages. Es gibt dabei keine Commits, das Repo bleibt klein.
- `index.html` ist das Terminal: Chart, Indikatoren, Bot, Depot, Autopilot.

## Manuell aktualisieren

Gehe auf **Actions → Kurse aktualisieren → Run workflow**.

## Hinweis

GitHub pausiert geplante Workflows in öffentlichen Repos nach 60 Tagen ohne Aktivität. Falls die Kurse stehen bleiben, starte den Workflow einmal manuell oder pushe eine kleine Änderung.

Lernprojekt. Keine Anlageberatung.
