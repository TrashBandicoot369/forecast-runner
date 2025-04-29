import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase app either from ENV or local JSON."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # Try environment variable (for Vercel)
    b64 = os.getenv("FIREBASE_CONFIG_B64")
    if b64:
        cfg = json.loads(base64.b64decode(b64).decode("utf-8"))
        cred = credentials.Certificate(cfg)
    else:
        # Fallback: Load from local service account JSON
        cred_path = os.path.join(os.path.dirname(__file__), "..", "chan500-firebase-adminsdk-fbsvc-5f4b8c5c86.json")
        cred_path = os.path.abspath(cred_path)
        with open(cred_path, "r") as f:
            cfg = json.load(f)
        cred = credentials.Certificate(cfg)

    firebase_admin.initialize_app(cred)

# Initialize on import
initialize_firebase()

# Firestore client
db = firestore.client()
