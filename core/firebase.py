import os
import firebase_admin
from firebase_admin import credentials, db

_app = None

def init_firebase():
    global _app
    if _app is not None:
        return _app
    cred_path = os.environ.get("FIREBASE_CREDENTIALS")
    db_url = os.environ.get("FIREBASE_DB_URL")
    if not cred_path or not db_url:
        raise RuntimeError("FIREBASE_CREDENTIALS and FIREBASE_DB_URL must be set in environment.")
    cred = credentials.Certificate(cred_path)
    _app = firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    return _app

def rtdb():
    init_firebase()
    return db


