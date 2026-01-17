# Path: api/server.py
# Version: 20.3
# Description: Сервер. Исправлен импорт Core (добавлен путь к корню).

import sys
import os

# --- FIX IMPORT PATHS ---
# Добавляем родительскую папку (корень проекта) в пути поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
# ------------------------

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import hashlib

from core import schema
from core.storage import Storage
from database.repository import DataRepository

app = FastAPI(title="Sync Server")

@app.get("/")
def root(): return RedirectResponse(url="/status")

@app.get("/status")
def status():
    return {
        "status": "online", 
        "server": "PC-Master", 
        "time": DataRepository.get_last_event_end() or "No data"
    }

@app.get("/config/fas")
def get_fas_config():
    return Storage.load_json(schema.FAS_PATH)

@app.get("/config/hash")
def get_fas_hash():
    if not os.path.exists(schema.FAS_PATH):
        return {"hash": None}
    try:
        with open(schema.FAS_PATH, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return {"hash": file_hash.hexdigest()}
    except Exception as e:
        return {"error": str(e), "hash": None}

@app.get("/sync/pull")
def pull_changes(since: str = None):
    changes = DataRepository.get_changes_since(since)
    return {"count": len(changes), "records": changes}

@app.post("/sync/push")
def push_changes(records: List[Dict[str, Any]]):
    try:
        count = DataRepository.apply_sync_batch(records)
        return {"status": "success", "processed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))