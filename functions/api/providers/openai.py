import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """OpenAI API Provider for Fallback Reasoning & Assistant Tasks"""

    @staticmethod
    def generate_completion(prompt: str, system_prompt: str = "You are DigiIndia AI Assistant."):
        if not settings.OPENAI_API_KEY:
            return {
                "response": "OpenAI Assistant response: Project documentation and architecture review generated successfully.",
                "status": "mock"
            }
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"]
                    return {"response": text, "status": "success"}
        except Exception as e:
            logger.error(f"OpenAI API call exception: {e}")

        return {
            "response": "AI Assistance generated for project optimization.",
            "status": "fallback"
        }
