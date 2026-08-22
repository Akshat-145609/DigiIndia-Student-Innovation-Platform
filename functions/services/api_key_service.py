import time
import uuid
import secrets
import hashlib
from api.providers.firebase import FirestoreRepository
from models.schemas import APIKeyCreateSchema

keys_repo = FirestoreRepository("apiKeys")

class APIKeyService:

    @classmethod
    def generate_api_key(cls, owner_uid: str, schema: APIKeyCreateSchema):
        raw_key = f"di_live_{secrets.token_hex(16)}"
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = str(uuid.uuid4())
        expires_at = time.time() + ((schema.expiresInDays or 365) * 86400)

        key_doc = {
            "keyId": key_id,
            "ownerUID": owner_uid,
            "apiName": schema.apiName,
            "hashedKey": hashed_key,
            "keyPrefix": raw_key[:12] + "...",
            "permissions": schema.permissions or ["search", "projects"],
            "usageCount": 0,
            "status": "active",
            "createdAt": time.time(),
            "expiresAt": expires_at,
            "lastUsed": None
        }
        keys_repo.set(key_id, key_doc)

        return {
            "keyId": key_id,
            "apiName": schema.apiName,
            "rawAPIKey": raw_key, # Shown ONCE to the student
            "keyPrefix": key_doc["keyPrefix"],
            "permissions": key_doc["permissions"],
            "expiresAt": expires_at
        }

    @staticmethod
    def list_user_keys(owner_uid: str):
        keys = keys_repo.query(filters=[("ownerUID", "==", owner_uid)])
        # Strip hashedKey for security
        results = []
        for k in keys:
            results.append({
                "keyId": k.get("keyId"),
                "apiName": k.get("apiName"),
                "keyPrefix": k.get("keyPrefix"),
                "permissions": k.get("permissions"),
                "usageCount": k.get("usageCount", 0),
                "status": k.get("status"),
                "createdAt": k.get("createdAt"),
                "expiresAt": k.get("expiresAt"),
                "lastUsed": k.get("lastUsed")
            })
        return results

    @staticmethod
    def revoke_key(owner_uid: str, key_id: str):
        key_doc = keys_repo.get(key_id)
        if not key_doc or key_doc.get("ownerUID") != owner_uid:
            raise Exception("API key not found or unauthorized")
        key_doc["status"] = "revoked"
        key_doc["updatedAt"] = time.time()
        keys_repo.set(key_id, key_doc)
        return {"message": "API key revoked successfully", "keyId": key_id}
