import time
import uuid
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from api.providers.firebase import FirestoreRepository
from api.router import AIRouter

ai_models_repo = FirestoreRepository("aiTrainingModels")
knowledge_repo = FirestoreRepository("aiKnowledge")

class CrawlerService:

    @classmethod
    def crawl_and_process_url(cls, target_url: str, depth: int = 1, max_pages: int = 5):
        stages = []

        # Stage 1: Fetch Main URL Source Code
        stage1_title = f"[Stage 1/4] Fetching Main URL Source Code: {target_url}"
        stages.append(stage1_title)
        
        main_source = ""
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                res = client.get(target_url)
                if res.status_code == 200:
                    main_source = res.text
        except Exception as e:
            main_source = f"<!-- Error fetching URL {target_url}: {e} -->"

        # Stage 2: Extract & Validate Hyperlinks
        stage2_title = f"[Stage 2/4] Validating & Extracting Hyperlinks from DOM tree..."
        stages.append(stage2_title)

        found_links = []
        if main_source:
            try:
                soup = BeautifulSoup(main_source, "html.parser")
                base_domain = urlparse(target_url).netloc
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    full_url = urljoin(target_url, href)
                    parsed_full = urlparse(full_url)
                    if parsed_full.scheme in ["http", "https"] and full_url not in found_links:
                        found_links.append(full_url)
                        if len(found_links) >= max_pages:
                            break
            except Exception:
                pass

        # Stage 3: Fetch Linked Sub-Pages Source Code
        stage3_title = f"[Stage 3/4] Crawling {len(found_links)} Sub-page Hyperlinks..."
        stages.append(stage3_title)

        subpages_code = {}
        for link in found_links[:max_pages]:
            try:
                with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                    sub_res = client.get(link)
                    if sub_res.status_code == 200:
                        subpages_code[link] = sub_res.text[:3000]
            except Exception:
                pass

        # Stage 4: Send to AI Processor & Generate Knowledge
        stage4_title = f"[Stage 4/4] Synthesizing Source Code into AI Knowledge Base..."
        stages.append(stage4_title)

        knowledge_id = f"kw_{str(uuid.uuid4())[:8]}"
        
        # Prepare combined context for AI model
        combined_source = f"--- MAIN URL: {target_url} ---\n{main_source[:8000]}\n\n"
        for lk, code in subpages_code.items():
            combined_source += f"--- SUBPAGE LINK: {lk} ---\n{code}\n\n"

        prompt = f"Analyze the following source code and extract key architectural features, technology stack, logic, routes, and data schemas into a structured markdown document.\n\nSource Code:\n{combined_source[:12000]}"
        
        ai_response = AIRouter.process_assistant_chat(prompt, context_type="code_crawler")
        knowledge_md = ai_response.get("reply", f"# Code Analysis Knowledge for {target_url}\n\nSource code extracted successfully with {len(found_links)} sub-links.")

        # Store in Firestore Repository
        record = {
            "knowledgeId": knowledge_id,
            "targetURL": target_url,
            "mainSourceLength": len(main_source),
            "subPagesCrawled": len(subpages_code),
            "hyperlinksFound": found_links,
            "knowledgeMarkdown": knowledge_md,
            "stages": stages,
            "createdAt": time.time()
        }
        knowledge_repo.set(knowledge_id, record)
        ai_models_repo.set(f"url_{knowledge_id}", {
            "modelName": f"Crawler: {urlparse(target_url).netloc}",
            "type": "crawled_url",
            "targetURL": target_url,
            "knowledgeId": knowledge_id,
            "createdAt": time.time()
        })

        return record
