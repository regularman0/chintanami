# Path: api/server.py
# Version: 20.1
# Description: FastAPI сервер. Добавлен редирект с главной страницы на статус.

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

# Импорты ядра
from core import schema
from core.storage import Storage
from database.repository import DataRepository

app = FastAPI(title="Sync Server")

# --- ГЛАВНАЯ СТРАНИЦА (Редирект) ---
@app.get("/")
def root():
    """Если открыли просто адрес сервера, перекидываем на статус"""
    return RedirectResponse(url="/status")

@app.get("/status")
def status():
    """Проверка связи"""
    return {
        "status": "online", 
        "server": "PC-Master", 
        "time": DataRepository.get_last_event_end() or "No data"
    }

@app.get("/config/fas")
def get_fas_config():
    """Отдает файл структуры категорий телефону"""
    return Storage.load_json(schema.FAS_PATH)

@app.get("/sync/pull")
def pull_changes(since: str = None):
    """
    Телефон запрашивает изменения.
    since: ISO дата последнего обновления на телефоне.
    """
    print(f">>> [API] Client requested changes since: {since}")
    changes = DataRepository.get_changes_since(since)
    return {"count": len(changes), "records": changes}

@app.post("/sync/push")
def push_changes(records: List[Dict[str, Any]]):
    """
    Телефон присылает свои изменения.
    """
    print(f">>> [API] Receiving {len(records)} records from client")
    try:
        count = DataRepository.apply_sync_batch(records)
        return {"status": "success", "processed": count}
    except Exception as e:
        print(f"[API Error] Push failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))