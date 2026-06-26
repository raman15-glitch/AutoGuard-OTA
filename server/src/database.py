import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "fleet.db")

def init_db():
    """Creates the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    # Table 1
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            current_version TEXT NOT NULL,
            cohort TEXT NOT NULL DEFAULT 'general',
            last_seen TIMESTAMP NOT NULL
        )
    ''')

    #Table 2 
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_version TEXT NOT NULL,
            target_cohort TEXT NOT NULL,
            is_active BOOLEAN NOT NULL CHECK (is_active IN(0,1)),
            created_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("[Database] Schema upgraded: Devices and Campaigns tables ready.")

def seed_test_data():
    """ Inject our test car and a beta campiagn into the DB"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    now = datetime.now()

    devices = [
        ('TSLA-999','1.0','beta',now),
        ('RIVN-404','1.0','general',now),
        ('FORD-101','1.0','general',now)
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO devices(device_id, current_version, cohort,last_seen)
        VALUES (?,?,?,?)
    ''',devices)

    cursor.execute('''
        INSERT OR IGNORE INTO campaigns (campaign_id, target_version, target_cohort, is_active, created_at)
        VALUES (1,'2.0','beta',1,?)
    ''',(now,))

    conn.commit()
    conn.close()
    print("[Database] Seeded test fleet and active Beta compaigns")

def update_device_status(device_id, version):
    """Inserts or updates a car's record when it connects."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''
        UPDATE devices 
        SET current_version = ?, last_seen = ?
        WHERE device_id = ?
    ''',(version,now,device_id))

    
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO devices (device_id, current_version, cohort, last_seen)
            VALUES (?, ?, 'general', ?)
        ''', (device_id, version, datetime.now()))
    
    conn.commit()
    conn.close()

def get_active_campaign_for_device(device_id):
    "Find if this specific device should get an update"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.target_version
        FROM devices d
        JOIN campaigns c ON d.cohort = c.target_cohort 
        WHERE d.device_id = ? AND c.is_active = 1
        ORDER BY c.created_at DESC LIMIT 1 
    ''', (device_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    return None

def get_fleet_status():
    """Fetches all devices for a dashboard."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM devices')
    rows = cursor.fetchall()
    conn.close()
    return rows

# Initialize the database when this file is imported
init_db()
seed_test_data()