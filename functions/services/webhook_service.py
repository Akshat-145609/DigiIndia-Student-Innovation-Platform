import time
import uuid
import httpx
from api.providers.firebase import FirestoreRepository

webhooks_repo = FirestoreRepository("webhookSubscriptions")

class WebhookService:
    """
    Webhook Event Subscriptions Service.
    Dispatches real-time webhook events (project.created, project.verified, comment.added)
    to registered third-party developer platforms (like Codagenda).
    """

    @classmethod
    def register_webhook(cls, user_uid: str, target_url: str, event_types: list, secret: str = "") -> dict:
        sub_id = f"sub_{str(uuid.uuid4())[:8]}"
        sub_doc = {
            "subscriptionId": sub_id,
            "userUID": user_uid,
            "targetURL": target_url,
            "eventTypes": event_types,
            "secret": secret or str(uuid.uuid4()),
            "status": "active",
            "createdAt": time.time()
        }
        webhooks_repo.set(sub_id, sub_doc)
        return sub_doc

    @classmethod
    def dispatch_event(cls, event_type: str, payload: dict):
        subs = webhooks_repo.query(filters=[("status", "==", "active")])
        headers = {"User-Agent": "DigiIndia-Webhook-Dispatcher/1.0", "Content-Type": "application/json"}

        for sub in subs:
            if event_type in sub.get("eventTypes", []) or "*" in sub.get("eventTypes", []):
                target_url = sub.get("targetURL")
                try:
                    event_data = {
                        "event": event_type,
                        "subscriptionId": sub.get("subscriptionId"),
                        "timestamp": time.time(),
                        "data": payload
                    }
                    with httpx.Client(timeout=5.0) as client:
                        client.post(target_url, json=event_data, headers=headers)
                except Exception:
                    pass
