# OBDsidian

> **Your car is talking. You just can't hear it yet.**

OBDsidian is a three-layer OBD-II telemetry platform for people who can *feel* something wrong with their car but can't name it — and for the mechanics and knowledgeable friends in their lives who can.

Black box logger. Cinematic cockpit display. AI diagnostic agent. Open source core. Built for the dash, not the enterprise.

---

## What It Does

Most OBD apps show you live data and stop there. OBDsidian records everything, visualizes it in real time, and lets an AI agent tell you what it found — in plain English, tuned to who's asking.

**Layer 1 — Black Box Logger** *(always on, always recording)*
Every drive is logged automatically. Full telemetry per session, synced to Supabase when you're back on WiFi. Offline-first. No manual trigger. The foundation everything else is built on.

**Layer 2 — Cockpit Display** *(real-time, in the car)*
SVG arc gauges with GSAP-animated needles. Obsidian dark theme — amber, green, red. Designed for a center-console laptop mount. Glanceable for the driver. Diagnostic for the mechanic riding shotgun.

**Layer 3 — AI Diagnostic Agent** *(post-drive analysis)*
Reads your logged sessions and explains what it found. Two modes:
- **Driver mode** — *"Something's off with how your engine fires at low RPM. Here's what to tell your mechanic."*
- **Mechanic mode** — *"Misfire pattern on cylinder 2, consistent with ignition coil degradation. Fuel trim correlation suggests..."*

Same data. Two completely different conversations.

---

## Architecture

```
FNIRSI FD10 (plugged into OBD-II port)
    ↕  Bluetooth 5.1
Your Laptop (runs locally, offline-first)
    └── PIDgeon  ←  FastAPI + bleak (BLE) + ELM327 AT commands
            ↓  WebSocket
        SvelteKit  (localhost)
            ├── SVG Cockpit (Layer 2)
            ├── EVAP status panel
            ├── DTC reader
            └── Session log view
                    ↓  background sync
                Supabase
                    └── AI Diagnostic Agent (Layer 3)
                            ↓  persona toggle
                        Driver mode / Mechanic mode
```

The backend service is called **PIDgeon** — a standalone FastAPI process that handles all Bluetooth OBD communication via `bleak` (BLE GATT) and streams live PIDs over WebSocket. It's independently usable and publishable as its own tool.

---

## Tech Stack

| Layer | Tool | Role |
|---|---|---|
| Backend | `FastAPI` | Local API server, WebSocket endpoint |
| Backend | `bleak` | BLE GATT connection to OBD adapter |
| Backend | `ble-serial` | Virtual serial port bridge over BLE (optional) |
| Backend | ELM327 AT commands | Raw PID querying over BLE UART |
| Backend | `asyncio` | Async polling loop |
| Backend | `supabase-py` | Background session logging |
| Frontend | `SvelteKit` | App framework |
| Frontend | `GSAP` | SVG needle animations, gauge sweeps |
| Frontend | `TailwindCSS` | Layout |
| Database | `Supabase` | Session storage, historical telemetry, DTC log |
| AI | `Claude API` | Diagnostic reasoning over logged sessions |

---

## Hardware Requirements

- **OBD-II Bluetooth adapter** — Built and tested with the FNIRSI FD10 (Bluetooth 5.1 BLE). Other BLE ELM327 adapters may work but will likely require GATT characteristic profiling before first use. Classic Bluetooth (SPP) adapters are not supported.
- **A laptop** — Runs locally via Docker (cross-platform). macOS tested natively. If you get it running on Linux or Windows, open a PR.
- **A car with an OBD-II port** — that's every car made after 1996.

The OBD-II port is usually under the dash on the driver's side. If you're using a BLE adapter for the first time, scan its GATT services with [nRF Connect](https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-mobile) to confirm the read/write characteristic UUIDs before setup.

---

## Quick Start

> ⚠️ Setup docs coming in Phase 1. Placeholders below.

```bash
# Clone the repo
git clone https://github.com/your-handle/obdsidian.git
cd obdsidian

# Backend (PIDgeon)
cd pidgeon
pip install -r requirements.txt
cp .env.example .env  # add your Supabase credentials
uvicorn main:app --reload

# Frontend
cd ../ui
npm install
npm run dev
```

Pair your OBD adapter via Bluetooth, open `localhost:5173`, and drive.

---

## Open Source vs SaaS

| | Open Source | SaaS |
|---|---|---|
| **Price** | Free | ~$50/mo or under |
| **Cockpit display** | ✅ | ✅ |
| **Local logging** | ✅ | ✅ |
| **Supabase sync** | Self-hosted | Hosted |
| **Historical sessions + trends** | Self-hosted | Included |
| **AI diagnostic agent** | Bring your own API key | Included |
| **Web dashboard** | ❌ | ✅ |

The open source tier is the full app. Clone it, run it, self-host everything. The SaaS tier sells the data layer — hosted Supabase, session history across devices, and managed AI diagnostics for people who don't want to wrangle infrastructure.

---

## Roadmap

**Phase 0 — Hardware Validation** *(current)*
- [ ] Confirm FD10 pairs on macOS
- [ ] First successful PID query (RPM from a real car)
- [ ] Supabase project scaffolded and schema applied

**Phase 1 — Black Box Logger MVP**
- [ ] FastAPI + SvelteKit scaffolded
- [ ] WebSocket streaming live PIDs
- [ ] Continuous Supabase telemetry logging per session
- [ ] Session start/stop on Bluetooth connect/disconnect

**Phase 2 — Cockpit Display**
- [ ] Live SVG gauges with GSAP animations
- [ ] Full gauge suite: RPM, speed, coolant, throttle, fuel trim
- [ ] Obsidian dark theme, full layout
- [ ] EVAP status panel + DTC reader

**Phase 3 — AI Diagnostic Agent**
- [ ] Claude API integration
- [ ] Session telemetry → agent context pipeline
- [ ] Driver mode + Mechanic mode outputs
- [ ] Persona toggle in UI
- [ ] First real test: the Jeep Liberty low-RPM stutter

**Phase 4 — Product & Polish**
- [ ] Full GitHub publish + setup docs
- [ ] SaaS tier scaffolding
- [ ] Demo video

---

## The Mission

This started with a 2012 Jeep Liberty that stutters at low RPM under acceleration. Subtle, consistent, no check engine light, no codes. Stock apps are useless. The ECU isn't flagging anything — but the driver can feel it.

OBDsidian exists to catch **pre-fault patterns** that stock apps miss. When Layer 3 correctly identifies what's causing that stutter using data Layer 1 collected, the platform works.

That's the real test case. Everything is built toward it.

---

## Contributing

Pre-scaffold right now — issues and discussions open. If you've got a BLE OBD adapter and have cracked macOS Bluetooth serial, open an issue. The hardware layer is the first thing to solve.

---

## License

MIT — core is open source. Go build something.

---

*Built by [Nate](https://github.com/your-handle) · Powered by FastAPI, SvelteKit, Supabase, and Claude*
