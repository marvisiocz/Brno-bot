# Brno Rain Bot

Free Telegram alert ~15–30 min before it rains in Brno. Runs on GitHub Actions cron — no server, no API key for weather, no paid services.

## Stack

- **Cron**: GitHub Actions (`*/15 * * * *`)
- **Weather**: Open-Meteo `minutely_15` (free, no API key, ~1–2 km resolution via ICON-D2 for Central Europe)
- **Delivery**: Telegram Bot API
- **Language**: Python 3.12, only `requests` dependency

## Layout

```
.
├── CLAUDE.md                       ← this file
├── README.md                       ← human setup steps
├── check_rain.py                   ← entire bot logic, single file
├── requirements.txt                ← just `requests`
└── .github/workflows/rain-check.yml ← cron + manual trigger
```

## Design decisions (so we don't re-argue them)

- **Why GitHub Actions, not Cloudflare Workers / Render / Railway**: zero extra accounts, repo already on GitHub. Trade-off accepted = cron jitter (typically 5–15 min delay under GH load, occasionally more, very rarely a skipped run).
- **Why 15-minute interval**: rain forecasts need fresh data. Tighter than 15 min is wasteful (model doesn't update faster) and pushes against GH Actions cron precision.
- **Why `minutely_15` endpoint, not hourly**: hourly is too coarse for "alert 30 min before rain". Open-Meteo provides 15-min data for Central Europe from high-res models — this is exactly the use case.
- **Why deduplicate by past observation, not by state file**: no race conditions, no need for GH Actions cache / external store. Logic: if past 30 min was dry AND next 45 min has a wet 15-min block → alert. Naturally fires once per rain event.
- **Brno coordinates**: 49.1951 N, 16.6068 E (city centre).
- **Public repo recommended**: GitHub Actions free tier is unlimited for public repos. Private has 2000 min/month — this job uses ~960 min/month at 15-min interval, so it fits, but no headroom for other workflows.

## Tunable knobs (top of `check_rain.py`)

| Constant            | Default | Meaning                                                  |
| ------------------- | ------- | -------------------------------------------------------- |
| `LOOKAHEAD_MIN`     | 45      | How far ahead to look for the first rainy 15-min block   |
| `LOOKBACK_MIN`      | 30      | How far back must be dry for the alert to fire           |
| `WET_MM_BLOCK`      | 0.1     | 15-min precip threshold (mm) for "this block is wet"     |
| `DRY_MM_TOTAL`      | 0.2     | Total mm in lookback above which "it's already raining"  |

If false positives become annoying, the cheapest fix is gating on probability too:
`if (p or 0) >= WET_MM_BLOCK and (pr or 0) >= 50`.

## Known limitations

- GH Actions scheduled workflows can be delayed under load — realistic lead time is 5–30 min, not exactly 30. Not safety-critical infra.
- Precip models can "flicker" between consecutive runs — duplicate alerts within the same event are dampened by the past-observation dedup, but not 100% prevented during marginal cases.
- Czech timezone hardcoded (`Europe/Prague`).
- Open-Meteo non-commercial terms apply.

## Future ideas (not done, document before implementing)

- Cooldown via GitHub Actions cache (store last-alert timestamp, suppress within N minutes)
- Thunderstorm / hail / strong-wind alerts via `weathercode`
- Multiple recipients via comma-separated `TELEGRAM_CHAT_ID`
- Snow detection separate from rain
- Migration to Cloudflare Workers Cron Triggers if jitter becomes a real problem (more precise scheduling, free tier 100k req/day, but JS rewrite)

## Conventions for changes

- **Single-file Python script** — keep it that way unless complexity demands a split.
- **Stdlib + `requests` only** — no extra deps without a real reason.
- **All thresholds at top of `check_rain.py`** — easy to tweak from the file head.
- **Log every decision** — every run should print either `Skip — <reason>` or `Sent: <message>`. Makes Actions logs self-explanatory.
- **Never commit secrets** — `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` live only in GitHub repo Secrets.

## Test workflow

1. `Actions` tab → `Brno rain alert` → `Run workflow` → manual trigger.
2. For end-to-end delivery test: temporarily set `WET_MM_BLOCK = 0.0` so any non-zero forecast triggers a message, run manually, then revert.
3. Check Actions logs — the script prints its decision either way.
