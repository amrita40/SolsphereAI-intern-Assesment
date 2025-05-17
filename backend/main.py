# main.py (FastAPI Backend)
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3
import os

API_KEY = os.getenv("API_KEY", "supersecrettoken")
DB_FILE = "health_data.db"

app = FastAPI()

# Database setup
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
    machine_id TEXT,
    timestamp TEXT,
    os TEXT,
    disk_encryption INTEGER,
    os_up_to_date INTEGER,
    antivirus_enabled INTEGER,
    sleep_setting INTEGER
)''')
conn.commit()
conn.close()

# Auth dependency
def verify_token(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

# Pydantic model
class SystemReport(BaseModel):
    machine_id: str
    timestamp: str
    os: str
    disk_encryption: bool
    os_up_to_date: bool
    antivirus_enabled: bool
    sleep_setting: bool

@app.post("/report", dependencies=[Depends(verify_token)])
async def receive_report(report: SystemReport):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            report.machine_id,
            report.timestamp,
            report.os,
            int(report.disk_encryption),
            int(report.os_up_to_date),
            int(report.antivirus_enabled),
            int(report.sleep_setting)
        ))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/machines", dependencies=[Depends(verify_token)])
async def list_latest_reports(os: Optional[str] = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = """
        SELECT machine_id, MAX(timestamp), os, disk_encryption, os_up_to_date, antivirus_enabled, sleep_setting
        FROM reports
        GROUP BY machine_id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        if os and row[2].lower() != os.lower():
            continue
        results.append({
            "machine_id": row[0],
            "timestamp": row[1],
            "os": row[2],
            "disk_encryption": bool(row[3]),
            "os_up_to_date": bool(row[4]),
            "antivirus_enabled": bool(row[5]),
            "sleep_setting": bool(row[6])
        })
    return results

@app.get("/export.csv", dependencies=[Depends(verify_token)])
async def export_csv():
    import csv
    from fastapi.responses import StreamingResponse
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports")
    rows = cursor.fetchall()
    conn.close()

    def generate():
        yield "machine_id,timestamp,os,disk_encryption,os_up_to_date,antivirus_enabled,sleep_setting\n"
        for row in rows:
            yield ",".join(map(str, row)) + "\n"

    return StreamingResponse(generate(), media_type="text/csv")
