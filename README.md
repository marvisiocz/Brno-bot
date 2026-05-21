# Brno Rain Bot

Telegram alert ~15–30 min předtím, než v Brně začne pršet, s radarovým snímkem Brna + okolí v příloze. Běží jako GitHub Actions cron (každých 15 min). Bez serveru, bez API klíče pro počasí ani radar, bez placených služeb.

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
| `TELEGRAM_CHAT_ID`    | tvoje chat ID     |

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

## Limity

- GitHub Actions cron má jitter (typicky 5–15 min).
- Public repo = Actions zdarma neomezeně; private = 2000 min/měsíc.
- Rain Viewer a Open-Meteo free tier = non-commercial use.
