"""MongoDB-backed JSON state, enabled only when MONGODB_URI is configured.

One MongoDB document per logical JSON file. No fallback to ephemeral storage
when MongoDB is configured: connectivity errors must be visible.
"""
import json
import os
from pathlib import Path
from threading import RLock

_LOCK = RLock()
_CLIENT = None
_DB = None

def _database():
    global _CLIENT, _DB
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        return None
    with _LOCK:
        if _DB is None:
            from pymongo import MongoClient
            _CLIENT = MongoClient(uri, serverSelectionTimeoutMS=8000, retryWrites=True)
            _CLIENT.admin.command("ping")
            _DB = _CLIENT[os.environ.get("MONGODB_DB", "fampay_api")]
        return _DB

def read_state(path):
    db = _database()
    if db is None:
        try:
            with open(path, encoding="utf-8") as f:
                result = json.load(f)
            return result if isinstance(result, dict) else {}
        except FileNotFoundError:
            return {}
    key = Path(path).name
    doc = db["app_state"].find_one({"_id": key})
    if doc:
        return doc.get("value", {})
    # Import an existing local file once, only if a document does not exist.
    try:
        with open(path, encoding="utf-8") as f:
            initial = json.load(f)
        if not isinstance(initial, dict):
            initial = {}
    except FileNotFoundError:
        initial = {}
    if initial:
        try:
            db["app_state"].insert_one({"_id": key, "value": initial})
        except Exception:
            doc = db["app_state"].find_one({"_id": key})
            if doc:
                return doc.get("value", {})
            raise
    return initial

def write_state(path, value):
    db = _database()
    if db is not None:
        db["app_state"].replace_one(
            {"_id": Path(path).name},
            {"_id": Path(path).name, "value": value},
            upsert=True)
        return
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
