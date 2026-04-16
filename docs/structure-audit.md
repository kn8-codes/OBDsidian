# OBDsidian — Structure Audit
**Date:** 2026-04-16
**Branch:** main
**Auditor:** Claude Code (session: repo cleanup and structure audit)

---

## Actual repo tree

```
OBDsidian/
├── .git/
├── dashboard/                   # SvelteKit frontend
│   ├── .gitignore
│   ├── .npmrc
│   ├── .vscode/
│   ├── package.json
│   ├── package-lock.json
│   ├── README.md
│   ├── svelte.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── app.d.ts
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── assets/favicon.svg
│   │   │   └── index.ts
│   │   └── routes/
│   │       ├── +layout.svelte
│   │       └── +page.svelte
│   └── static/
│       └── robots.txt
├── docs/
│   ├── architecture-plan.md
│   └── structure-audit.md       # this file
├── pidgeon/                     # FastAPI backend
│   ├── .gitignore
│   ├── requirements.txt         # EMPTY — see bugs
│   └── app/
│       ├── __init__.py
│       ├── ble_test.py
│       ├── config.py
│       ├── main.py
│       ├── obd_client.py        # TRUNCATED — see bugs
│       └── supabase_client.py
├── README.md
└── start.sh
```

No pidgeon/pidgeon nesting. Structure is flat and correct.

---

## What is present and working

| File | Status | Notes |
|---|---|---|
| `pidgeon/app/main.py` | OK | FastAPI app, lifespan, /health, /data, /ws endpoints |
| `pidgeon/app/supabase_client.py` | OK (with bug) | session/telemetry/dtc/diagnostic insert functions |
| `pidgeon/app/config.py` | OK | dotenv loader, env var accessors |
| `pidgeon/app/ble_test.py` | OK | standalone BLE scanner + RPM test script |
| `pidgeon/app/__init__.py` | OK | empty, marks package correctly |
| `dashboard/package.json` | OK | SvelteKit + Vite deps |
| `dashboard/svelte.config.js` | OK | adapter-auto config |
| `dashboard/vite.config.ts` | OK | standard vite config |
| `docs/architecture-plan.md` | OK | accurate and detailed |
| `README.md` | Stale | wrong paths in Quick Start (see bugs) |
| `start.sh` | Partially broken | assumes venv that isn't in repo |

---

## Bugs found

### BUG 1 — obd_client.py is truncated and the OBDClient class is missing (CRITICAL)

**File:** `pidgeon/app/obd_client.py`
**Line count:** 44 (truncated)

The file ends mid-string on line 44 with a corrupted `"°F` followed by 14 invisible Unicode zero-width space characters (U+200B) and then a newline. The file cuts off inside the `decode()` function.

More critically: `main.py` imports `OBDClient` from `app.obd_client`:
```python
from app.obd_client import OBDClient
obd = OBDClient()
```
But `OBDClient` is not defined anywhere in `obd_client.py`. The class — including `connect()`, `disconnect()`, `start_polling()`, and `live_data` — is entirely absent from the file.

**Effect:** The backend cannot start. Any `uvicorn app.main:app` invocation will fail at import with `ImportError`.

**Action required:** Write the complete `OBDClient` class.

---

### BUG 2 — requirements.txt is empty

**File:** `pidgeon/requirements.txt`
**Size:** 0 bytes

The app imports: `fastapi`, `bleak`, `supabase`, `python-dotenv`, `uvicorn` (and `websockets` for FastAPI WS). None are listed.

**Effect:** `pip install -r requirements.txt` installs nothing. Environment setup fails silently.

**Action required:** Populate with actual dependencies and pinned versions.

---

### BUG 3 — README Quick Start has wrong paths

**File:** `README.md` lines 98–101

Two wrong references:
1. `cd ../ui` — the frontend directory is `dashboard/`, not `ui/`
2. `uvicorn main:app --reload` — the correct invocation from inside `pidgeon/` is `uvicorn app.main:app --reload`

**Effect:** Anyone following the README gets two broken commands in a row.

**Action required:** Fix both paths. (Fixed in this session — see README.md.)

---

### BUG 4 — .env.example does not exist

**File:** Referenced in `README.md` line 98: `cp .env.example .env`

No `.env.example` exists anywhere in the repo.

**Effect:** Setup instruction references a file that isn't there.

**Action required:** Add `pidgeon/.env.example` with placeholder keys.

---

### BUG 5 — end_session() writes "now()" as a literal string

**File:** `pidgeon/app/supabase_client.py` line 18

```python
"ended_at": "now()"
```

`"now()"` is a PostgreSQL function call — it is not interpolated by the Supabase Python client. It will be stored as the literal string `"now()"` in the `ended_at` column.

**Effect:** Session end timestamps are corrupted/invalid in Supabase.

**Action required:** Use `datetime.utcnow().isoformat()` or rely on a `DEFAULT now()` column definition and omit the field.

---

### BUG 6 — start.sh assumes a venv that isn't in the repo

**File:** `start.sh` line 6

```bash
source venv/bin/activate
```

No `venv/` directory is committed (correctly excluded by `.gitignore`), but the script gives no guidance on how to create one. It will error on a fresh clone.

**Effect:** `start.sh` fails for anyone who hasn't manually created and populated a venv.

**Action required:** Add setup note to README or add a guard/message to `start.sh`.

---

## What is missing vs architecture-plan.md

| Gap (from architecture doc) | Present? | Notes |
|---|---|---|
| `OBDClient` class with connect/poll/disconnect | No | BUG 1 above |
| Local telemetry buffer / offline spool | No | Gap 2 in arch doc |
| Supabase schema / migration files | No | Gap 5 in arch doc |
| `.env.example` | No | BUG 4 above |
| Dashboard live telemetry consumer | No | Default scaffold only |
| Dashboard WebSocket integration | No | Not started |
| Live gauge components | No | Not started |
| Session state model | No | Gap 4 in arch doc |
| Telemetry contract / PID registry | No | Gap 1 in arch doc |
| Reconnect/backoff logic | No | Noted in arch doc |

---

## What does NOT need cleanup

- No pidgeon/pidgeon nesting exists. The structure is flat and correct.
- No duplicate or orphaned files.
- `.gitignore` entries look correct for both `pidgeon/` and `dashboard/`.
- The architecture plan accurately reflects current code state.
- `ble_test.py` is in `app/` which is slightly odd for a standalone script, but not worth moving until there's a clearer scripts/ convention.

---

## Priority action list

1. **Write OBDClient class** — unblocks everything; app cannot start without it.
2. **Populate requirements.txt** — unblocks environment setup.
3. **Add .env.example** — unblocks fresh clone onboarding.
4. **Fix end_session() timestamp** — corrupts session data if left.
5. **Fix start.sh venv guidance** — friction for fresh installs.
6. (Already done this session) **Fix README Quick Start paths.**

Items 2–6 are small. Item 1 is the real work.
