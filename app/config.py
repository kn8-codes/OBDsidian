from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OBD_PORT = os.getenv("OBD_PORT", "auto")
FAST_POLL_INTERVAL = float(os.getenv("FAST_POLL_INTERVAL", 0.1))
SLOW_POLL_INTERVAL = float(os.getenv("SLOW_POLL_INTERVAL", 2.0))
