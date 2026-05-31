# Brno Rain Bot

Free Telegram alert ~15–30 min before it rains in Brno, with a radar snapshot of Brno + okolí attached. Runs on GitHub Actions cron — no server, no API key for weather/radar, no paid services.

## Stack

- **Cron**: GitHub Actions (`7,22,37,52 * * * *` — every 15 min, shifted off-peak); optionally triggered on-time by cron-job.org (see `NAVOD-cron-job-org.md`)
- **Forecast**: Open-Meteo `minutely_15` (free, no API key, ~1–2 km resolution via ICON-D2 for Central Europe)
- **Radar**: Rain Viewer free public API + OpenStreetMap base tiles, composited locally with Pillow
- **Delivery**: Telegram Bot API (`sendPhoto` with caption, fallback to `sendMessage` on radar failure)
- **Language**: Python 3.12, deps: `requests`, `Pillow`

## Layout

```
.
├── CLAUDE.md                       ← this file
├── README.md                       ← human setup steps
├── NAVOD-cron-job-org.md           ← Czech guide: trigger on-time via cron-job.org
├── check_rain.py                   ← Open-Meteo logic + Telegram send
├── radar.py                        ← Rain Viewer + OSM compositor
├── requirements.txt                ← requests, Pillow
└── .github/workflows/rain-check.yml ← cron + manual trigger
```

## Design decisions (so we don't re-argue them)

- **Why GitHub Actions, not Cloudflare Workers / Render / Railway**: zero extra accounts, repo already on GitHub. Trade-off accepted = cron jitter (typically 5–30 min delay under GH load, occasionally more, very rarely a skipped run). For on-time delivery without leaving GitHub, an external trigger (cron-job.org → `workflow_dispatch`) is documented in `NAVOD-cron-job-org.md`.
- **Why 15-minute interval**: rain forecasts need fresh data. Tighter is wasteful and pushes against GH Actions cron precision.
- **Why `minutely_15` endpoint**: hourly is too coarse for "alert 30 min before rain". Open-Meteo provides 15-min data for Central Europe from high-res models.
- **Why deduplicate via `state.json` (persisted in the GH Actions cache)**: fire at most one alert per rain event. Past-observation logic (dry last 30 min + a wet 15-min block in the next 45 min) decides *whether* rain is happening/imminent; `state.json` then records the last-alert timestamp so we don't re-alert within the same event. The marker is reset to 0 once the sky is genuinely clear (no rain now, none in the next 45 min), so the next event alerts fresh.
- **Why Rain Viewer, not ČHMÚ INCA**: ČHMÚ INCA is CC BY-NC-**ND** — no derivatives, so we can't legally crop it. Rain Viewer's free tier explicitly allows compositing/cropping; attribution is in the photo caption.
- **Why OSM base + Rain Viewer overlay, composited in Python**: Telegram can't render a live map; we have to send a static image. Doing the composite ourselves is ~150 lines of Pillow code, no third-party service, no API keys.
- **Why zoom 7, 2×2 tiles, 384 px crop**: Rain Viewer free tier max is zoom 7, 512 px tiles. One tile ≈ 200 km at Brno's latitude. 2×2 = ~400 km, cropped to 384 px ≈ 150 km square centered on Brno — similar framing to ČHMÚ INCA (roughly Tábor–Hodonín east-west, Olomouc–Mikulov north-south).
- **Why `sendPhoto` with fallback to `sendMessage`**: if Rain Viewer or OSM tile servers blip, we still want the text alert delivered. Caption carries the same payload as the old message.
- **Brno coordinates**: 49.1951 N, 16.6068 E (city centre).

## Tunable knobs

`check_rain.py` (forecast logic):

| Constant            | Default | Meaning                                                  |
| ------------------- | ------- | -------------------------------------------------------- |
| `LOOKAHEAD_MIN`     | 45      | How far ahead to look for the first rainy 15-min block   |
| `LOOKBACK_MIN`      | 30      | How far back must be dry for the alert to fire           |
| `WET_MM_BLOCK`      | 0.1     | 15-min precip threshold (mm) for "this block is wet"     |
| `DRY_MM_TOTAL`      | 0.2     | Total mm in lookback above which "it's already raining"  |

`radar.py` (image):

| Constant           | Default | Meaning                                              |
| ------------------ | ------- | ---------------------------------------------------- |
| `ZOOM`             | 7       | Tile zoom level (Rain Viewer free tier max = 7)      |
| `TILE_SIZE`        | 512     | Tile size in px                                       |
| `CROP_SIZE`        | 384     | Output square size in px                             |
| `RADAR_OPACITY`    | 0.75    | Radar overlay opacity, 0..1                          |
| `COLOR_SCHEME`     | 2       | Rain Viewer palette (2 = Universal Blue)             |

## Known limitations

- GH Actions scheduled workflows can be delayed under load — realistic lead time is 5–30 min.
- Precip models can "flicker" between runs — duplicate alerts are dampened by past-observation dedup, not 100% prevented.
- Czech timezone hardcoded (`Europe/Prague`).
- Rain Viewer free tier: no SLA. The `try/except` around radar gracefully falls back to text-only alert.
- OSM tile usage policy: low-volume use is fine (we set a unique User-Agent).

## License & attribution

- **Open-Meteo**: free non-commercial; no attribution required.
- **Rain Viewer**: free for personal / educational / small community use. Attribution "Weather data by Rain Viewer" is **mandatory** — already embedded in the photo caption.
- **OpenStreetMap**: ODbL. "© OpenStreetMap contributors" required — already embedded in the photo caption.

If this bot is ever pointed at a Marvisio-branded Telegram channel for commercial use, Rain Viewer terms require contacting them for commercial terms.

## Future ideas (not done, document before implementing)

- Time-based cooldown on top of the per-event dedup (suppress repeats within N minutes even inside one long event)
- Thunderstorm / hail / strong-wind alerts via `weathercode`
- Animated radar (GIF of last hour from Rain Viewer past frames)
- Multiple recipients via comma-separated `TELEGRAM_CHAT_ID`
- Migration to Cloudflare Workers Cron Triggers if jitter becomes a problem

## Conventions for changes

- **Stdlib + `requests` + `Pillow` only** — no extra deps without a real reason.
- **All thresholds at top of `check_rain.py` / `radar.py`** — easy to tweak.
- **Log every decision** — every run should print one of: `Skip — <reason>`, `Sent photo + caption: ...`, or `Radar fetch/send failed (...); falling back to text-only.` followed by `Sent: ...`.
- **Radar failures must never block the text alert** — wrap radar in `try/except`, fall back to `sendMessage`.
- **Never commit secrets** — tokens live only in GitHub repo Secrets.

## Test workflow

1. `Actions` tab → `Brno rain alert` → `Run workflow`.
2. End-to-end delivery test: temporarily set `WET_MM_BLOCK = 0.0` and `DRY_MM_TOTAL = 999`, run, revert.
3. Radar-only smoke test: `python radar.py` writes `brno-radar.png` to disk.
