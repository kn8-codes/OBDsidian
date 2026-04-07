import asyncio
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def create_session(vehicle: str = "2012 Jeep Liberty", notes: str = "") -> str:
    result = supabase.table("sessions").insert({
        "vehicle": vehicle,
        "notes": notes
    }).execute()
    session_id = result.data[0]["id"]
    print(f"Session started: {session_id}")
    return session_id

async def end_session(session_id: str):
    supabase.table("sessions").update({
        "ended_at": "now()"
    }).eq("id", session_id).execute()
    print(f"Session ended: {session_id}")

async def log_telemetry(session_id: str, pid: str, value: float, unit: str):
    supabase.table("telemetry").insert({
        "session_id": session_id,
        "pid": pid,
        "value": value,
        "unit": unit
    }).execute()

async def log_dtc(session_id: str, code: str, description: str):
    supabase.table("dtcs").insert({
        "session_id": session_id,
        "code": code,
        "description": description
    }).execute()

async def log_diagnostic(session_id: str, persona: str, findings: str, confidence: str):
    supabase.table("diagnostics").insert({
        "session_id": session_id,
        "persona": persona,
        "findings": findings,
        "confidence": confidence
    }).execute()
