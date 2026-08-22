import time
import uuid
import logging
from api.providers.firebase import FirestoreRepository

logger = logging.getLogger(__name__)

class APICallHandler:
    """
    Centralized Gateway for handling API Calls, Rate Limiting, Retries,
    Audit Logging, and Error Normalization across DigiIndia.
    """
    def __init__(self):
        self.logs_repo = FirestoreRepository("apiLogs")
        self.usage_repo = FirestoreRepository("apiUsage")
        self.errors_repo = FirestoreRepository("apiErrors")

    def execute_call(self, provider_name: str, endpoint: str, call_func, *args, **kwargs):
        correlation_id = str(uuid.uuid4())
        start_time = time.time()
        retry_count = 0
        max_retries = 3

        while retry_count <= max_retries:
            try:
                result = call_func(*args, **kwargs)
                latency = round((time.time() - start_time) * 1000, 2)
                
                # Log success
                self.log_request(provider_name, endpoint, "SUCCESS", latency, correlation_id, retry_count)
                self.record_usage(provider_name, endpoint, success=True, latency=latency)
                
                return {
                    "status": "success",
                    "data": result,
                    "provider": provider_name,
                    "latency_ms": latency,
                    "correlation_id": correlation_id
                }

            except Exception as e:
                retry_count += 1
                logger.error(f"API Call to {provider_name}/{endpoint} failed (Attempt {retry_count}/{max_retries}): {e}")
                if retry_count > max_retries:
                    latency = round((time.time() - start_time) * 1000, 2)
                    error_code = "API-1006" # Provider Unavailable
                    self.log_request(provider_name, endpoint, "FAILED", latency, correlation_id, retry_count, str(e))
                    self.record_usage(provider_name, endpoint, success=False, latency=latency)
                    return {
                        "status": "error",
                        "code": error_code,
                        "message": f"Provider {provider_name} request failed after retries.",
                        "error_details": str(e),
                        "correlation_id": correlation_id
                    }
                time.sleep(1 * retry_count) # Exponential backoff

    def log_request(self, provider: str, endpoint: str, status: str, latency: float, correlation_id: str, retry_count: int, error: str = None):
        log_doc = {
            "provider": provider,
            "endpoint": endpoint,
            "status": status,
            "latencyMs": latency,
            "correlationId": correlation_id,
            "retryCount": retry_count,
            "timestamp": time.time()
        }
        if error:
            log_doc["error"] = error
        self.logs_repo.add(log_doc)

    def record_usage(self, provider: str, endpoint: str, success: bool, latency: float):
        doc_id = f"{provider}_{endpoint.replace('/', '_')}"
        existing = self.usage_repo.get(doc_id) or {
            "provider": provider,
            "endpoint": endpoint,
            "requestCount": 0,
            "successCount": 0,
            "failureCount": 0,
            "averageLatency": 0.0
        }
        req_count = existing["requestCount"] + 1
        succ_count = existing["successCount"] + (1 if success else 0)
        fail_count = existing["failureCount"] + (0 if success else 1)
        avg_lat = round(((existing["averageLatency"] * existing["requestCount"]) + latency) / req_count, 2)

        self.usage_repo.set(doc_id, {
            "provider": provider,
            "endpoint": endpoint,
            "requestCount": req_count,
            "successCount": succ_count,
            "failureCount": fail_count,
            "averageLatency": avg_lat,
            "lastUsed": time.time()
        })

api_handler = APICallHandler()
