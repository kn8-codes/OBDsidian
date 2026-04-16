# OBDsidian Architecture Plan

## Purpose
Define the working architecture for OBDsidian as a three-layer telemetry system:

1. **In-car hardware + transport** — FNIRSI FD10 over BLE
2. **Acquisition + sync layer** — Python/bleak collector with Supabase persistence
3. **App + analysis layer** — SvelteKit/FastAPI UI and diagnostics surface

This plan reflects the repo state on the i7 Air as of 2026-04-15, not just the long-term vision.

---

## System goal
OBDsidian should become an offline-capable black box logger and diagnostic surface that:
- talks to the FNIRSI FD10 over BLE
- continuously polls useful OBD/ELM327 PIDs
- stores sessions and telemetry in Supabase
- presents live and historical data in a SvelteKit UI
- eventually supports higher-level diagnostic interpretation

---

## Three-layer design

## Layer 1 — Vehicle + BLE acquisition
### Flow
`FNIRSI FD10 BLE adapter -> bleak client -> ELM327 commands -> decoded PID values`

### Responsibilities
- discover and connect to the FD10 over BLE
- write ELM327/OBD commands to the correct GATT characteristic
- receive notifications from the response characteristic
- decode raw PID responses into usable values
- maintain connection lifecycle for drive sessions

### Current implementation status
Exists in `pidgeon/app/obd_client.py`.

What is present now:
- BLE client approach via `bleak`
- hardcoded FD10 GATT UUIDs
- grouped fast/slow PID polling model
- decoder stubs for at least:
  - RPM
  - speed
  - throttle
  - coolant
- polling concept tied to async runtime

What is still weak or incomplete:
- hardware validation is not proven in this repo state
- no clear reconnect/backoff/session recovery plan shown yet
- no durable adapter discovery/selection UX
- decode coverage is still partial
- likely needs cleanup, tests, and real-car validation before trusted logging

### Design recommendation
Keep this layer narrow and explicit:
- one adapter profile first: **FNIRSI FD10 only**
- one stable BLE transport path first
- one known-good core PID set first

Do not broaden adapter compatibility until FD10 polling is reliable.

---

## Layer 2 — Local collector + persistence
### Flow
`decoded PID stream -> FastAPI service -> Supabase session/telemetry tables`

### Responsibilities
- own session lifecycle
- expose local health/data/websocket endpoints
- stream current data to the dashboard
- write sessions and telemetry to Supabase
- eventually support offline buffering and delayed sync

### Current implementation status
Exists mainly in:
- `pidgeon/app/main.py`
- `pidgeon/app/supabase_client.py`
- `pidgeon/app/config.py`

What is present now:
- FastAPI app scaffold
- startup lifespan hook
- `/health` endpoint
- `/data` endpoint
- `/ws` websocket endpoint
- Supabase inserts for:
  - sessions
  - telemetry
  - dtcs
  - diagnostics
- backend startup pattern that tries to connect and start a session

What is missing or fragile:
- true offline-first behavior is not implemented yet
- writes go directly to Supabase, no queue/spool layer
- session shutdown handling looks simplistic
- `end_session()` currently writes `"now()"` as a literal string, which likely needs a proper timestamp/server-side default strategy
- no explicit batching strategy for telemetry writes
- no backpressure/rate management for high-frequency polling
- no schema validation layer between BLE decode and persistence
- no auth/config hardening around Supabase credentials yet

### Design recommendation
This layer should become the system backbone.

Target shape:
- **collector process** owns BLE and decoding
- **local buffer** stores telemetry when offline or rate-limited
- **sync worker** flushes to Supabase in batches
- **FastAPI** serves local state and control endpoints only

That means OBDsidian needs a clearer split inside Layer 2:
1. acquisition loop
2. local event/session buffer
3. sync/persistence adapter
4. API/websocket interface

Right now those concerns are too blended.

---

## Layer 3 — UI + analysis surface
### Flow
`FastAPI/ws + Supabase historical data -> SvelteKit dashboard -> later diagnostic workflows`

### Responsibilities
- show live telemetry cleanly in-car
- show session history later
- support diagnostic review and trend analysis
- eventually expose AI-assisted interpretation without making the core product depend on it

### Current implementation status
Present as `dashboard/`, but mostly scaffold-level.

What is present now:
- SvelteKit app skeleton
- package/config files
- frontend run path in `start.sh`

What is not yet present in a meaningful way:
- real cockpit UI
- integrated websocket telemetry display
- historical session views
- diagnostic workflows
- Supabase-backed dashboard views
- productionized component structure

### Design recommendation
Build Layer 3 in two passes:

#### Pass A — Live cockpit MVP
- health banner
- connection state
- 4 to 6 core gauges
- session start/stop visibility
- basic DTC status panel

#### Pass B — Review + diagnosis
- historical session list
- session detail playback/traces
- anomaly flags
- diagnostic notes / AI summary hooks

Do not start with a giant UI. Start with a stable live telemetry cockpit.

---

## Current repo state

## What’s done
- repo structure exists
- backend and frontend are separated cleanly enough to reason about
- FastAPI service exists
- BLE client exists
- Supabase client exists
- dashboard project exists
- start script exists for combined local run
- overall product direction is already well-defined in `README.md`

## What’s partially done
- PID polling/decode path
- websocket live stream path
- Supabase logging path
- config plumbing

## What’s not done yet
- real validated FD10 end-to-end session capture
- stable offline buffering/sync
- meaningful dashboard implementation
- schema/documented Supabase contract in repo
- diagnostics pipeline beyond placeholder logging
- deployment/dev environment clarity

---

## Architecture gaps to close next

## Gap 1 — Source of truth for telemetry model
There needs to be one explicit telemetry contract.

Define:
- PID name
- raw command
- decode function
- unit
- polling tier
- display label
- storage field strategy

Without that, frontend, backend, and persistence will drift.

## Gap 2 — Offline-first storage
The README promises offline-first behavior, but the current code writes straight to Supabase.

Need:
- local spool file or SQLite store
- session-aware buffering
- retry queue
- flush on reconnection/Wi-Fi availability

## Gap 3 — Dashboard implementation lag
The dashboard repo exists, but it does not yet match the product concept.

Need:
- live websocket consumer
- gauge primitives
- connection/session status components
- telemetry cards / graphs
- historical session views later

## Gap 4 — Session lifecycle discipline
Need a more explicit state model:
- disconnected
- scanning
- connecting
- connected
- logging
- degraded
- syncing
- ended

This will simplify both UI and backend recovery logic.

## Gap 5 — Supabase schema + docs
The repo needs explicit schema docs or migrations for:
- sessions
- telemetry
- dtcs
- diagnostics
- maybe vehicles / adapters later

Right now the code implies schema, but the schema itself is not captured in a durable way here.

---

## Prioritized sprint plan

## Sprint 1 — Hardware truth first
Goal: prove FNIRSI FD10 works reliably enough to build on.

Priority tasks:
1. validate BLE connect/disconnect behavior on the actual FD10
2. validate notify/write characteristics against real hardware
3. prove one real PID end to end (RPM first)
4. prove a minimal fast PID set:
   - RPM
   - speed
   - throttle
   - coolant
5. log raw adapter responses for debugging
6. document exact FD10 handshake/setup behavior

Deliverable:
- one captured real-car session with trustworthy RPM/speed/throttle/coolant data

## Sprint 2 — Session logging backbone
Goal: make capture trustworthy and resumable.

Priority tasks:
1. add local session buffer/spool
2. define telemetry event schema
3. batch writes to Supabase
4. fix session open/close semantics
5. add reconnect and retry behavior
6. create schema/migration docs for Supabase tables

Deliverable:
- local collector that can survive connection issues and still preserve drive data

## Sprint 3 — Live cockpit MVP
Goal: usable in-car dashboard.

Priority tasks:
1. connect dashboard to websocket feed
2. build live gauge components
3. add connection/session state UI
4. add simple DTC panel
5. add visual fault/degraded-state indicators

Deliverable:
- dashboard that is actually useful during a drive

## Sprint 4 — Historical review + diagnostics
Goal: useful after the drive.

Priority tasks:
1. historical session list
2. session detail page
3. trend visualizations
4. diagnostic notes/logging
5. groundwork for driver/mechanic interpretation modes

Deliverable:
- post-drive review workflow using recorded sessions

---

## Recommended immediate next actions
1. audit and finish `pidgeon/app/obd_client.py`
2. define the telemetry/session schema in writing
3. add a local spool strategy before calling the app offline-first
4. build the first real dashboard data consumer against `/ws`
5. test with the Jeep and capture one canonical session

---

## Practical build order
If time and energy are limited, build in this order:

1. **FD10 connection stability**
2. **RPM/speed/throttle/coolant logging**
3. **local buffering + Supabase sync**
4. **basic live dashboard**
5. **historical session review**
6. **AI diagnostics**

That keeps the project grounded in real vehicle data instead of drifting into premature analysis features.

---

## Bottom line
OBDsidian already has the right product shape.
The repo proves the concept direction, but the implementation is still in the phase where hardware truth and logging reliability matter more than polish.

The next win is not more vision.
The next win is one trustworthy, recorded drive session from the FNIRSI FD10 through PIDgeon into Supabase, with the dashboard visibly consuming that stream.
