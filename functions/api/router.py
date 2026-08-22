import logging
from api.providers.gemini import GeminiProvider
from api.providers.grok import GrokProvider
from api.providers.nvidia import NvidiaAIProvider
from api.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

class AIRouter:
    """Dynamic AI Provider Router with Secondary Fallback Strategy"""

    @staticmethod
    def analyze_repository(repo_url: str, readme: str = "", metadata: dict = None):
        logger.info(f"Routing repo analysis for {repo_url} via Gemini Provider")
        res = GeminiProvider.analyze_repository(repo_url, readme, metadata)
        if not res or "error" in res:
            logger.info("Gemini failed/unavailable. Falling back to OpenAI Provider")
            res = OpenAIProvider.generate_completion(f"Analyze repository: {repo_url}\n{readme[:1000]}")
            return {"summary": res.get("response"), "fallback": True}
        return res

    @staticmethod
    def review_code(code_snippet: str, language: str = "python"):
        logger.info(f"Routing code review for {language} via Grok Provider")
        res = GrokProvider.review_code_reasoning(code_snippet, language)
        if not res or "error" in res:
            logger.info("Grok failed/unavailable. Falling back to OpenAI Provider")
            res = OpenAIProvider.generate_completion(f"Review code:\n{code_snippet[:1500]}")
            return {"review": res.get("response"), "quality_score": 80, "fallback": True}
        return res

    @staticmethod
    def process_vision_ocr(file_data: str, doc_type: str = "abc_id"):
        logger.info(f"Routing vision OCR for {doc_type} via NVIDIA Provider")
        return NvidiaAIProvider.process_document_ocr(file_data, doc_type)

    @staticmethod
    def generate_assistant_response(prompt: str, context: str = ""):
        full_prompt = f"Context: {context}\nUser Request: {prompt}"
        res = OpenAIProvider.generate_completion(full_prompt)
        return res
