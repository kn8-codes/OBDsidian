import os
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class SessionLogger:
    def __init__(self):
        self.session_id = None

    def start_session(self, vehicle: str = "2012 Jeep Liberty") -> str:
        result = supabase.table("sessions").insert({
            "vehicle": vehicle,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        self.session_id = result.data[0]["id"]
        print(f"Session started: {self.session_id}")
        return self.session_id

    def end_session(self):
        if not self.session_id:
            return
        supabase.table("sessions").update({
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", self.session_id).execute()
        print(f"Session ended: {self.session_id}")
        self.session_id = None

    def log_telemetry(self, pid: str, value: float, unit: str = ""):
        if not self.session_id:
            return
        supabase.table("telemetry").insert({
            "session_id": self.session_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "pid": pid,
            "value": value,
            "unit": unit,
        }).execute()

    def log_dtc(self, code: str, description: str = ""):
        if not self.session_id:
            return
        supabase.table("dtcs").insert({
            "session_id": self.session_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "code": code,
            "description": description,
        }).execute()
