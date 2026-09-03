import time
import httpx
from bs4 import BeautifulSoup
from api.providers.firebase import FirestoreRepository
from api.router import AIRouter

projects_repo = FirestoreRepository("projects")
verifications_repo = FirestoreRepository("projectVerification")

class VerificationService:

    @classmethod
    def verify_project_ownership(cls, project_id: str):
        verif = verifications_repo.get(project_id)
        proj = projects_repo.get(project_id)

        if not verif or not proj:
            raise Exception("Project or verification record not found")

        token = verif.get("verificationToken")
        live_url = proj.get("liveURL") or proj.get("repositoryURL")

        if not live_url or not live_url.startswith("http"):
            raise Exception("Valid target URL (http/https) required for crawler verification")

        attempts = verif.get("attemptCount", 0) + 1
        verif["attemptCount"] = attempts
        verif["lastAttempt"] = time.time()

        verified = False
        reason = ""
        robots_found = False
        sitemap_found = False
        sitemap_urls_count = 0
        screenshot_uri = ""
        
        # Runtime SEO Elements
        runtime_seo = {
            "title": "",
            "description": "",
            "author": "",
            "keywords": "",
            "canonical": "",
            "viewport": "",
            "openGraph": {},
            "twitterCard": {},
            "h1Count": 0,
            "h1Text": "",
            "metaTagToken": ""
        }
        
        # SEO Comparison Audit Results
        seo_comparison = {
            "titleMatch": False,
            "descriptionMatch": False,
            "ownershipMatch": False,
            "canonicalConfigured": False,
            "socialGraphConfigured": False,
            "contentStructureValid": False,
            "crawlerAssetsConfigured": False
        }
        
        score_breakdown = {}
        awarded_score = 20 # base trust score

        try:
            from urllib.parse import urljoin, urlparse
            import re
            parsed_base = urlparse(live_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"

            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                res = client.get(live_url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    
                    # 1. Extract Runtime SEO Elements
                    if soup.title and soup.title.string:
                        runtime_seo["title"] = soup.title.string.strip()
                    
                    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
                    if meta_desc:
                        runtime_seo["description"] = meta_desc.get("content", "").strip()
                        
                    meta_auth = soup.find("meta", attrs={"name": re.compile(r"^author$", re.I)})
                    if meta_auth:
                        runtime_seo["author"] = meta_auth.get("content", "").strip()
                        
                    meta_kw = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
                    if meta_kw:
                        runtime_seo["keywords"] = meta_kw.get("content", "").strip()
                        
                    meta_vp = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
                    if meta_vp:
                        runtime_seo["viewport"] = meta_vp.get("content", "").strip()
                        
                    canon_tag = soup.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
                    if canon_tag:
                        runtime_seo["canonical"] = canon_tag.get("href", "").strip()

                    # OpenGraph & Twitter
                    og_tags = {}
                    for og in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
                        og_tags[og.get("property", "").lower()] = og.get("content", "")
                    runtime_seo["openGraph"] = og_tags

                    tw_tags = {}
                    for tw in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
                        tw_tags[tw.get("name", "").lower()] = tw.get("content", "")
                    runtime_seo["twitterCard"] = tw_tags

                    # Headings
                    h1_list = soup.find_all("h1")
                    runtime_seo["h1Count"] = len(h1_list)
                    runtime_seo["h1Text"] = h1_list[0].get_text().strip() if h1_list else ""

                    # Verification Ownership Tag
                    meta_tag = soup.find("meta", attrs={"name": "digiindia-student-innovation-platform"})
                    if meta_tag:
                        runtime_seo["metaTagToken"] = meta_tag.get("content", "").strip()
                        if runtime_seo["metaTagToken"] == token:
                            verified = True
                            seo_comparison["ownershipMatch"] = True
                            reason = "Ownership meta tag verified successfully!"
                        else:
                            reason = f"Meta tag token '{runtime_seo['metaTagToken']}' does not match expected '{token}'"
                    else:
                        reason = f"Meta tag 'digiindia-student-innovation-platform' not found on {live_url}"

                    # 2. Compare Runtime SEO with Coded Source Code / Project Metadata
                    proj_title = (proj.get("title") or "").strip().lower()
                    proj_desc = (proj.get("description") or "").strip().lower()

                    if runtime_seo["title"] and (proj_title in runtime_seo["title"].lower() or runtime_seo["title"].lower() in proj_title or len(runtime_seo["title"]) >= 5):
                        seo_comparison["titleMatch"] = True
                        
                    if runtime_seo["description"] and (len(runtime_seo["description"]) >= 20 or any(w in runtime_seo["description"].lower() for w in proj_desc.split()[:4])):
                        seo_comparison["descriptionMatch"] = True

                    if runtime_seo["canonical"] or runtime_seo["viewport"]:
                        seo_comparison["canonicalConfigured"] = True

                    if og_tags or tw_tags:
                        seo_comparison["socialGraphConfigured"] = True

                    if runtime_seo["h1Count"] >= 1:
                        seo_comparison["contentStructureValid"] = True

                    # Snapshot
                    import base64
                    snapshot_html = f"<html><body><h3>Snapshot Preview for {live_url}</h3><p>{soup.get_text()[:400]}</p></body></html>"
                    screenshot_uri = f"data:text/html;base64,{base64.b64encode(snapshot_html.encode('utf-8')).decode('utf-8')}"

                # Test robots.txt
                try:
                    robots_res = client.get(urljoin(base_domain, "/robots.txt"))
                    if robots_res.status_code == 200 and len(robots_res.text) > 5:
                        robots_found = True
                except Exception:
                    pass

                # Test sitemap.xml
                try:
                    sitemap_res = client.get(urljoin(base_domain, "/sitemap.xml"))
                    if sitemap_res.status_code == 200:
                        sitemap_found = True
                        sitemap_urls_count = len(re.findall(r'<loc>(.*?)</loc>', sitemap_res.text))
                except Exception:
                    pass

                if robots_found or sitemap_found:
                    seo_comparison["crawlerAssetsConfigured"] = True

        except Exception as e:
            reason = f"Crawler error connecting to {live_url}: {str(e)}"

        # 3. Dynamic Score Awards Algorithm (Max 100 Points)
        score_breakdown["baseScore"] = 20
        if verified:
            score_breakdown["ownershipVerified"] = 30
            awarded_score += 30
        if seo_comparison["titleMatch"]:
            score_breakdown["titleOptimization"] = 15
            awarded_score += 15
        if seo_comparison["descriptionMatch"]:
            score_breakdown["metaDescriptionQuality"] = 15
            awarded_score += 15
        if seo_comparison["socialGraphConfigured"]:
            score_breakdown["socialMediaGraph"] = 10
            awarded_score += 10
        if seo_comparison["canonicalConfigured"]:
            score_breakdown["technicalSEO"] = 5
            awarded_score += 5
        if seo_comparison["contentStructureValid"]:
            score_breakdown["contentStructure"] = 5
            awarded_score += 5
        if seo_comparison["crawlerAssetsConfigured"]:
            score_breakdown["crawlerAssets"] = 5
            awarded_score += 5

        awarded_score = min(100, awarded_score)

        if verified:
            verif["verificationStatus"] = "verified"
            verif["verifiedAt"] = time.time()
        else:
            verif["verificationStatus"] = "failed"
            verif["failureReason"] = reason

        verif["crawlerLog"] = reason
        verif["hasRobotsTxt"] = robots_found
        verif["hasSitemapXml"] = sitemap_found
        verif["sitemapUrlsCount"] = sitemap_urls_count
        verif["liveSnapshotURI"] = screenshot_uri
        verif["runtimeSEO"] = runtime_seo
        verif["seoComparison"] = seo_comparison
        verif["scoreBreakdown"] = score_breakdown
        verif["awardedScore"] = awarded_score

        # Update Project record with SEO Trust Score
        projects_repo.set(project_id, {
            "verificationStatus": verif["verificationStatus"],
            "trustScore": awarded_score,
            "seoScore": awarded_score,
            "hasRobotsTxt": robots_found,
            "hasSitemapXml": sitemap_found,
            "updatedAt": time.time()
        })
        verifications_repo.set(project_id, verif)

        return {
            "projectId": project_id,
            "verificationStatus": verif["verificationStatus"],
            "verified": verified,
            "trustScore": awarded_score,
            "scoreBreakdown": score_breakdown,
            "runtimeSEO": runtime_seo,
            "seoComparison": seo_comparison,
            "hasRobotsTxt": robots_found,
            "hasSitemapXml": sitemap_found,
            "sitemapUrlsCount": sitemap_urls_count,
            "log": reason
        }


    @classmethod
    def process_identity_ocr(cls, doc_type: str, file_base64_or_url: str):
        ocr_result = AIRouter.process_vision_ocr(file_base64_or_url, doc_type)
        return {
            "docType": doc_type,
            "ocrResult": ocr_result,
            "timestamp": time.time()
        }
