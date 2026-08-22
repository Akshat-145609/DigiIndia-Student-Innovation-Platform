import logging
import firebase_admin
from firebase_admin import credentials, auth, firestore
from config import settings

logger = logging.getLogger(__name__)

import os
import json
import base64

# Initialize Firebase Admin SDK
try:
    if not firebase_admin._apps:
        cred = None
        service_acc_env = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
        service_acc_file = os.path.join(os.path.dirname(__file__), "..", "..", "firebase-service-account.json")
        
        if service_acc_env:
            try:
                decoded_json = base64.b64decode(service_acc_env).decode('utf-8')
                cred_dict = json.loads(decoded_json)
                cred = credentials.Certificate(cred_dict)
            except Exception:
                try:
                    cred_dict = json.loads(service_acc_env)
                    cred = credentials.Certificate(cred_dict)
                except Exception:
                    pass
        elif os.path.exists(service_acc_file):
            try:
                cred = credentials.Certificate(service_acc_file)
            except Exception:
                pass

        if cred:
            firebase_admin.initialize_app(cred, {'projectId': settings.FIREBASE_PROJECT_ID})
        elif settings.FIREBASE_PROJECT_ID:
            firebase_admin.initialize_app(options={'projectId': settings.FIREBASE_PROJECT_ID})
        else:
            firebase_admin.initialize_app()

    db = firestore.client()
    logger.info("Firebase Admin SDK & Firestore client initialized successfully.")
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization warning: {e}. Using fallback client mode.")
    try:
        db = firestore.client()
    except Exception:
        db = None


class FirebaseProvider:
    @staticmethod
    def verify_id_token(id_token: str):
        """Verify Firebase Auth JWT ID Token"""
        if not id_token:
            return None
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Error verifying Firebase ID Token: {e}")
            return None

    @staticmethod
    def get_user_by_email(email: str):
        try:
            return auth.get_user_by_email(email)
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    @staticmethod
    def create_user(email: str, password: str, display_name: str = None):
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            return user
        except Exception as e:
            logger.error(f"Error creating Firebase User: {e}")
            raise e

    @staticmethod
    def delete_user(uid: str):
        try:
            auth.delete_user(uid)
            return True
        except Exception as e:
            logger.error(f"Error deleting user {uid}: {e}")
            return False

import os
import json
import uuid

DATA_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data_store")
os.makedirs(DATA_STORE_DIR, exist_ok=True)

def _load_collection(collection_name: str) -> dict:
    file_path = os.path.join(DATA_STORE_DIR, f"{collection_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_collection(collection_name: str, data: dict):
    file_path = os.path.join(DATA_STORE_DIR, f"{collection_name}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing to disk store {file_path}: {e}")

def _sync_firestore_rest(collection_name: str, doc_id: str, data: dict):
    """Pushes document data directly to Cloud Firestore REST API for instant cloud persistence"""
    import httpx
    url = f"https://firestore.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/databases/(default)/documents/{collection_name}/{doc_id}"
    
    def encode_val(v):
        if isinstance(v, bool): return {"booleanValue": v}
        elif isinstance(v, (int, float)): return {"doubleValue": float(v)}
        elif isinstance(v, list): return {"arrayValue": {"values": [encode_val(x) for x in v]}}
        elif isinstance(v, dict): return {"mapValue": {"fields": {k: encode_val(val) for k, val in v.items()}}}
        else: 
            s = str(v if v is not None else "")
            if len(s.encode("utf-8")) > 1000000:
                s = s[:500000]
            return {"stringValue": s}


    fields = {k: encode_val(v) for k, v in data.items()}
    body = {"fields": fields}
    try:
        with httpx.Client(timeout=4.0) as client:
            client.patch(url, json=body)
    except Exception as e:
        logger.debug(f"Firestore REST sync note: {e}")

class FirestoreRepository:
    """Helper repository interface for Cloud Firestore with persistent disk fallback"""
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.col_ref = db.collection(collection_name) if db else None

    def get(self, doc_id: str):
        col = _load_collection(self.collection_name)
        if doc_id in col:
            return col[doc_id]
        if self.col_ref:
            try:
                doc = self.col_ref.document(doc_id).get(timeout=2.0)
                if doc.exists:
                    return {"id": doc.id, **doc.to_dict()}
            except Exception:
                pass
        return None

    def set(self, doc_id: str, data: dict, merge: bool = True):
        # 1. Update Disk Store first for zero latency & permanent persistence
        col = _load_collection(self.collection_name)
        if merge and doc_id in col:
            col[doc_id].update(data)
        else:
            col[doc_id] = data
        _save_collection(self.collection_name, col)

        # 2. Push to Cloud Firestore SDK if available
        if self.col_ref:
            try:
                self.col_ref.document(doc_id).set(data, merge=merge)
            except Exception:
                pass

        # 3. Push to Cloud Firestore REST API directly
        try:
            _sync_firestore_rest(self.collection_name, doc_id, col[doc_id])
        except Exception:
            pass

        return doc_id

    def add(self, data: dict, doc_id: str = None):
        if not doc_id:
            doc_id = str(uuid.uuid4())
        return self.set(doc_id, {"id": doc_id, **data})

    def delete(self, doc_id: str):
        col = _load_collection(self.collection_name)
        if doc_id in col:
            del col[doc_id]
            _save_collection(self.collection_name, col)

        if self.col_ref:
            try:
                self.col_ref.document(doc_id).delete()
            except Exception:
                pass
        return True


    def query(self, filters: list = None, limit: int = 500):
        """Query collection combining local disk store and Cloud Firestore docs"""
        disk_col = _load_collection(self.collection_name)
        combined_dict = dict(disk_col)

        if self.col_ref:
            try:
                docs = self.col_ref.stream(timeout=3.0)
                for doc in docs:
                    d = doc.to_dict()
                    d_id = doc.id
                    if d_id not in combined_dict:
                        combined_dict[d_id] = d
                    else:
                        combined_dict[d_id].update(d)
            except Exception as e:
                logger.debug(f"Firestore query stream note: {e}")

        results = []
        for doc_id, doc_data in combined_dict.items():
            match = True
            if filters:
                for field, op, val in filters:
                    doc_val = doc_data.get(field)
                    val_str = str(val).lower() if isinstance(val, str) else val
                    doc_val_str = str(doc_val).lower() if isinstance(doc_val, str) else doc_val

                    if op == "==":
                        if doc_val_str != val_str and doc_val != val:
                            match = False
                    elif op == "!=":
                        if doc_val_str == val_str or doc_val == val:
                            match = False
                    elif op == "in":
                        val_list = [str(x).lower() for x in val] if isinstance(val, (list, set, tuple)) else [str(val).lower()]
                        if doc_val_str not in val_list:
                            match = False
            if match:
                results.append({"id": doc_id, **doc_data})
            if len(results) >= limit:
                break
        return results


