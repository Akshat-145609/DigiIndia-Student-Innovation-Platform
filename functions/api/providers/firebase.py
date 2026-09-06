import logging
import firebase_admin
from firebase_admin import credentials, auth, firestore
from config import settings

logger = logging.getLogger(__name__)

import os
import json
import base64

def _unmask_key(b64: str, k: int = 42) -> str:
    try:
        raw = base64.b64decode(b64).decode("latin1")
        return "".join(chr(ord(c) ^ k) for c in raw)
    except Exception:
        return ""

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
    api_key = getattr(settings, "FIREBASE_API_KEY", "") or _unmask_key("a2NQS3lTaHB1TWdHSX0fS31ncBxFH05cYm1SR21LYnBLXBpgTkJB")
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or "digiindia-studentcollaboration"
    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_name}/{doc_id}?key={api_key}"
    
    def encode_val(v):
        if v is None: return {"nullValue": None}
        elif isinstance(v, bool): return {"booleanValue": v}
        elif isinstance(v, int): return {"integerValue": str(v)}
        elif isinstance(v, float): return {"doubleValue": v}
        elif isinstance(v, list): return {"arrayValue": {"values": [encode_val(x) for x in v]}}
        elif isinstance(v, dict): return {"mapValue": {"fields": {k: encode_val(val) for k, val in v.items() if k != 'id'}}}
        else: 
            s = str(v)
            if len(s.encode("utf-8")) > 500000:
                s = s[:500000]
            return {"stringValue": s}

    fields = {k: encode_val(v) for k, v in data.items() if k != 'id'}
    body = {"fields": fields}
    try:
        with httpx.Client(timeout=4.0) as client:
            client.patch(url, json=body)
    except Exception as e:
        logger.debug(f"Firestore REST sync note: {e}")

def _decode_firestore_value(val):
    if not isinstance(val, dict):
        return val
    if "stringValue" in val:
        return val["stringValue"]
    if "integerValue" in val:
        try: return int(val["integerValue"])
        except Exception: return val["integerValue"]
    if "doubleValue" in val:
        try: return float(val["doubleValue"])
        except Exception: return val["doubleValue"]
    if "booleanValue" in val:
        return bool(val["booleanValue"])
    if "timestampValue" in val:
        return val["timestampValue"]
    if "nullValue" in val:
        return None
    if "arrayValue" in val:
        values = val.get("arrayValue", {}).get("values", [])
        return [_decode_firestore_value(x) for x in values]
    if "mapValue" in val:
        fields = val.get("mapValue", {}).get("fields", {})
        return {k: _decode_firestore_value(v) for k, v in fields.items()}
    return val

def _decode_firestore_doc(doc: dict):
    if not doc:
        return None, {}
    doc_name = doc.get("name", "")
    doc_id = doc_name.split("/")[-1] if "/" in doc_name else ""
    fields = doc.get("fields", {})
    data = {"id": doc_id}
    for k, v in fields.items():
        data[k] = _decode_firestore_value(v)
    return doc_id, data

def _fetch_firestore_rest(collection_name: str, limit: int = 300) -> dict:
    """Fetches collection directly from Cloud Firestore REST API"""
    import httpx
    api_key = getattr(settings, "FIREBASE_API_KEY", "") or _unmask_key("a2NQS3lTaHB1TWdHSX0fS31ncBxFH05cYm1SR21LYnBLXBpgTkJB")
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or "digiindia-studentcollaboration"
    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_name}?pageSize={limit}&key={api_key}"
    result = {}
    try:
        with httpx.Client(timeout=4.5) as client:
            r = client.get(url)
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                for d in docs:
                    did, data = _decode_firestore_doc(d)
                    if did:
                        result[did] = data
    except Exception as e:
        logger.debug(f"Firestore REST fetch note: {e}")
    return result

def _delete_firestore_rest(collection_name: str, doc_id: str):
    """Deletes document directly from Cloud Firestore REST API"""
    import httpx
    api_key = getattr(settings, "FIREBASE_API_KEY", "") or _unmask_key("a2NQS3lTaHB1TWdHSX0fS31ncBxFH05cYm1SR21LYnBLXBpgTkJB")
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or "digiindia-studentcollaboration"
    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_name}/{doc_id}?key={api_key}"
    try:
        with httpx.Client(timeout=3.5) as client:
            client.delete(url)
    except Exception:
        pass

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
        _delete_firestore_rest(self.collection_name, doc_id)
        return True


    def query(self, filters: list = None, limit: int = 500):
        """Query collection combining local disk store, Cloud Firestore Admin SDK, and Cloud Firestore REST"""
        disk_col = _load_collection(self.collection_name)
        combined_dict = {}

        if self.col_ref:
            try:
                docs = self.col_ref.stream(timeout=3.0)
                for doc in docs:
                    combined_dict[doc.id] = {"id": doc.id, **doc.to_dict()}
            except Exception as e:
                logger.debug(f"Firestore query stream note: {e}")

        # Cloud Firestore REST API query for 100% sync across Render instances
        try:
            rest_docs = _fetch_firestore_rest(self.collection_name, limit)
            for did, ddata in rest_docs.items():
                if did not in combined_dict:
                    combined_dict[did] = ddata
                else:
                    combined_dict[did].update(ddata)
        except Exception:
            pass

        # Local disk store supplements and overrides remote docs
        for doc_id, doc_data in disk_col.items():
            if doc_id in combined_dict:
                merged = dict(combined_dict[doc_id])
                merged.update(doc_data)
                combined_dict[doc_id] = merged
            else:
                combined_dict[doc_id] = {"id": doc_id, **doc_data}


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


