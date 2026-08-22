import os
import json
import httpx
from config import settings

DATA_STORE_DIR = os.path.join(os.path.dirname(__file__), "data_store")

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


def sync_all():
    print(f"Starting Firestore REST upload sync for project: {settings.FIREBASE_PROJECT_ID}...")
    if not os.path.exists(DATA_STORE_DIR):
        print("No local data store directory found.")
        return

    success_count = 0
    fail_count = 0

    for fname in os.listdir(DATA_STORE_DIR):
        if fname.endswith(".json"):
            col_name = fname[:-5]
            fpath = os.path.join(DATA_STORE_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"Syncing collection '{col_name}' ({len(data)} documents)...")
            for doc_id, doc_data in data.items():
                url = f"https://firestore.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/databases/(default)/documents/{col_name}/{doc_id}"
                fields = {k: encode_val(v) for k, v in doc_data.items()}
                body = {"fields": fields}
                try:
                    with httpx.Client(timeout=60.0) as client:

                        res = client.patch(url, json=body)
                        if res.status_code in [200, 201]:
                            print(f"  [SUCCESS] Uploaded '{col_name}/{doc_id}' -> HTTP {res.status_code}")
                            success_count += 1
                        else:
                            print(f"  [FAIL] '{col_name}/{doc_id}' -> HTTP {res.status_code}: {res.text[:100]}")
                            fail_count += 1
                except Exception as e:
                    print(f"  [ERROR] Exception on '{col_name}/{doc_id}': {e}")
                    fail_count += 1


    print(f"\nFinal Sync Result: {success_count} documents uploaded successfully, {fail_count} failed.")

if __name__ == "__main__":
    sync_all()
