# Brno Rain Bot

Telegram alert ~15–30 min předtím, než v Brně začne pršet, s radarovým snímkem Brna + okolí v příloze. Běží jako GitHub Actions cron (použij cron-job, github actions automaticky funguje jen 2x-3x za den). Bez serveru, bez API klíče pro počasí ani radar, bez placených služeb.

## Jak to funguje

1. Každých 15 min se spustí GitHub Actions workflow.
2. Skript se zeptá [Open-Meteo](https://open-meteo.com/) na 15-minutový forecast srážek pro Brno.
3. Pokud byly poslední ~30 min suché **a** v dalších ~45 min model čeká déšť → stáhne z [Rain Viewer](https://rainviewer.com/) aktuální radarové dlaždice, slepí je s mapou OSM, ořízne na Brno + okolí (~150 km) a pošle ti to jako foto na Telegram.
4. Pokud radar selže (Rain Viewer výpadek, OSM ratelimit), pošle aspoň textovou zprávu — varování nikdy nepropadne.
5. Jinak nedělá nic.

## První setup (jednorázově)

### 1. Vytvoř Telegram bota

V Telegramu najdi **@BotFather** → `/newbot` → název → username (musí končit na `bot`) → dostaneš **TOKEN**.

### 2. Zjisti svoje chat ID

Nejrychleji: v Telegramu vyhledej `@userinfobot`, pošli `/start`, odpoví číslem — to je tvoje **CHAT_ID**.

### 3. Ulož tokeny do GitHub Secrets

V repu: **Settings → Secrets and variables → Actions → New repository secret**:

| Name                  | Value             |
| --------------------- | ----------------- |
| `TELEGRAM_BOT_TOKEN`  | token z BotFather |
| `TELEGRAM_CHAT_ID`    | tvoje chat ID (víc příjemců odděl čárkou, např. `123456789,987654321`) |

> Bot pošle stejnou zprávu na všechna uvedená chat ID. Každý příjemce musí botovi nejdřív poslat `/start`, jinak mu Telegram nedovolí psát. Skupinové chaty mají ID záporné (`-100…`).

### 4. Test

V repu **Actions → Brno rain alert → Run workflow**. V logu uvidíš `Skip — no rain in next 45 min.` nebo `Sent photo + caption: ...`.

Pro test doručení dočasně v `check_rain.py` nastav:
```python
WET_MM_BLOCK  = 0.0
DRY_MM_TOTAL  = 999
```
spusť ručně, vrať zpět.

## Ladění

- Prahy alertu nahoře v `check_rain.py`.
- Velikost / zoom / průhlednost radaru nahoře v `radar.py`.
- Detaily v `CLAUDE.md`.

## Atribuce (povinné dle licencí)

V popisku každého foto je: *Weather data by Rain Viewer · © OpenStreetMap contributors*.

## Přesnější časování (volitelně, přes cron-job.org)

GitHub cron se opožďuje a jede max 2x až 3x za den. Když chceš, aby upozornění chodila včas, může
workflow v přesný čas spouštět bezplatná služba [cron-job.org](https://cron-job.org)
přes GitHub API. Krok za krokem: [`NAVOD-cron-job-org.md`](NAVOD-cron-job-org.md).

## Limity

- GitHub Actions cron má jitter (max 3x za den).
- Public repo = Actions zdarma neomezeně; private = 2000 min/měsíc.
- Rain Viewer a Open-Meteo free tier = non-commercial use.
