# Brno Rain Bot

Telegram alert ~15–30 min předtím, než v Brně začne pršet. Běží jako GitHub Actions cron (každých 15 min). Bez serveru, bez API klíče pro počasí, bez placených služeb.

## Jak to funguje

1. Každých 15 min se spustí GitHub Actions workflow.
2. Skript se zeptá [Open-Meteo](https://open-meteo.com/) na 15-minutový forecast srážek pro Brno.
3. Pokud byly poslední ~30 min suché **a** v dalších ~45 min model čeká déšť → pošle ti zprávu na Telegram.
4. Jinak nedělá nic.

## První setup (jednorázově)

### 1. Vytvoř Telegram bota

V Telegramu najdi **@BotFather** → `/newbot` → název → username (musí končit na `bot`) → dostaneš **TOKEN** ve tvaru `123456789:ABC-DEF...`.

### 2. Zjisti svoje chat ID

- V Telegramu pošli novému botovi libovolnou zprávu (např. `/start`).
- V prohlížeči otevři: `https://api.telegram.org/bot<TVUJ_TOKEN>/getUpdates`
- V JSON odpovědi najdi `"chat":{"id": 123456789, ...}` — to je **CHAT_ID**.

### 3. Ulož tokeny do GitHub Secrets

V repu: **Settings → Secrets and variables → Actions → New repository secret**, přidej dva:

| Name                  | Value           |
| --------------------- | --------------- |
| `TELEGRAM_BOT_TOKEN`  | token z BotFather |
| `TELEGRAM_CHAT_ID`    | tvoje chat ID    |

### 4. Test

V repu **Actions → Brno rain alert → Run workflow** — workflow běžne hned. V logu uvidíš buď `Skip — no rain in next 45 min.` nebo `Sent: ...`.

Pro vyzkoušení doručení dočasně uprav v `check_rain.py`:
```python
WET_MM_BLOCK = 0.0
```
spusť ručně, vrať na `0.1`.

## Ladění

Všechny prahy jsou nahoře v `check_rain.py`. Detaily a designová rozhodnutí v `CLAUDE.md`.

## Limity

- GitHub Actions cron má jitter (typicky 5–15 min) — alert je tedy spíš `15–30 min předem`, ne přesně 30.
- Pro public repo je Actions zdarma neomezeně, pro private 2000 min/měsíc (tady ~960 min/měsíc).
- Open-Meteo: zdarma pro non-commercial.
