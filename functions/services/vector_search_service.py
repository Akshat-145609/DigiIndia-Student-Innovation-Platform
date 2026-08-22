import math
import re
from collections import Counter
from api.providers.firebase import FirestoreRepository

projects_repo = FirestoreRepository("projects")
metadata_repo = FirestoreRepository("projectMetadata")

class VectorSearchEngine:
    """
    Semantic Vector Search (RAG Engine) using TF-IDF Term Vectors and Cosine Similarity.
    Computes vector match similarity percentage (0% - 100%) for natural language queries.
    """

    @staticmethod
    def _tokenize(text: str) -> list:
        if not text:
            return []
        text = text.lower()
        words = re.findall(r'\b[a-z0-9+#\.]+\b', text)
        stopwords = {"a", "an", "the", "in", "on", "of", "for", "with", "and", "or", "is", "to", "at", "by", "from", "this", "that"}
        return [w for w in words if w not in stopwords and len(w) > 1]

    @staticmethod
    def _compute_tf(tokens: list) -> dict:
        counts = Counter(tokens)
        total = len(tokens) or 1
        return {term: count / total for term, count in counts.items()}

    @classmethod
    def _cosine_similarity(cls, vec1: dict, vec2: dict) -> float:
        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
        sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        return numerator / denominator

    @classmethod
    def semantic_search(cls, query: str, limit: int = 20) -> list:
        if not query or not query.strip():
            return []

        query_tokens = cls._tokenize(query)
        if not query_tokens:
            return []

        query_vec = cls._compute_tf(query_tokens)
        projects = projects_repo.query(filters=[("visibility", "==", "public")], limit=200)

        results = []
        for p in projects:
            p_id = p.get("projectId")
            meta = metadata_repo.get(p_id) or {}

            # Construct document corpus
            corpus_text = f"{p.get('title', '')} {p.get('description', '')} {' '.join(p.get('technologyStack', []))} {' '.join(p.get('tags', []))} {meta.get('aiSummary', '')}"
            doc_tokens = cls._tokenize(corpus_text)

            if not doc_tokens:
                continue

            doc_vec = cls._compute_tf(doc_tokens)
            similarity = cls._cosine_similarity(query_vec, doc_vec)

            # Boost if exact keyword match in title
            title_lower = p.get('title', '').lower()
            if any(t in title_lower for t in query_tokens):
                similarity = min(1.0, similarity + 0.25)

            if similarity > 0.05:
                p_copy = dict(p)
                p_copy["similarityScore"] = round(similarity, 4)
                p_copy["similarityPercentage"] = int(round(similarity * 100))
                results.append(p_copy)

        # Sort by highest vector similarity score
        results.sort(key=lambda x: x["similarityScore"], reverse=True)
        return results[:limit]
