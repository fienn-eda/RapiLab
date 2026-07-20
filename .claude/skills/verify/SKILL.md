---
name: verify
description: Launch and drive this project's FastAPI backend to verify a change end-to-end (surface = POST /api/recommend and /api/recommend-raid)
---

# Verifying backend changes at the API surface

## Launch

```bash
cd backend
"C:/Users/fienn/anaconda3/python.exe" -m uvicorn app.api:app --port 8731 --log-level warning &
# readiness: curl -s http://127.0.0.1:8731/openapi.json -o /dev/null -w "%{http_code}"
```

- Python is `C:/Users/fienn/anaconda3/python.exe` (plain `python` on PATH is a
  bare 3.14 without the project deps; `requests` is available in anaconda).
- Data files live in `<repo>/data/` (gitignored but present in worktrees too).

## Drive

`POST /api/recommend` body shape (see `backend/app/api.py`):

```json
{"roster": [{"character_slug": "liter", "level": 200,
             "hp": 1000000, "atk": 300000, "def_": 30000,
             "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10}}],
 "boss": {"element": "Water", "enemy_def": 31784.0},
 "top_n": 3}
```

- `boss.enemy_def` should be 31784.0 for realistic solo-raid numbers (defaults
  to 0.0).
- `POST /api/recommend-raid` takes the same body plus `num_decks` (1–5). Each
  deck needs a valid B1/B2/B3 shape — include at least `num_decks` B1 units.
- Unloadable slugs come back in `excluded_slugs` (never an error); bad field
  values (e.g. skill level 11) are a 422.

## Timing

A recommend over ~11 units takes ~25 s; recommend-raid with 12 units /
2 decks ~50 s. Keep verification rosters small (evaluate_deck is ~100 ms per
sim and the search fans out fast). Kill the server afterwards — on Windows,
`Stop-Process` on the python process whose CommandLine matches "uvicorn".
