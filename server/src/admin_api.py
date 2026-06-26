import sqlite3
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="AutoGuard Admin Control Plane")

# Lock the DB path exactly like the gRPC server
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "fleet.db")

def get_db_connection():
    """Helper to get a database connection that returns dictionaries."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    return conn

# --- DATA MODELS ---
class CampaignCreate(BaseModel):
    target_version: str
    target_cohort: str
    is_active: bool = True

@app.get("/", include_in_schema=False)
def root_redirect():
    """Automatically routes users from the root to the Swagger dashboard."""
    return RedirectResponse(url="/docs")

# --- API ENDPOINTS ---

@app.get("/fleet")
def get_fleet_status():
    """Returns the current status and version of all vehicles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "fleet": devices}

@app.get("/campaigns")
def get_active_campaigns():
    """Returns all rollout campaigns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    campaigns = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"status": "success", "campaigns": campaigns}

@app.post("/campaigns")
def create_rollout_campaign(campaign: CampaignCreate):
    """Creates a new OTA rollout campaign for a specific cohort."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO campaigns (target_version, target_cohort, is_active, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (campaign.target_version, campaign.target_cohort, 1 if campaign.is_active else 0))
        conn.commit()
        campaign_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    
    conn.close()
    return {
        "status": "success", 
        "message": f"Campaign created for cohort '{campaign.target_cohort}'",
        "campaign_id": campaign_id
    }