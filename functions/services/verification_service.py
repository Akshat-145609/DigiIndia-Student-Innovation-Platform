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

        try:
            from urllib.parse import urljoin, urlparse
            parsed_base = urlparse(live_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"

            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                res = client.get(live_url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    meta_tag = soup.find("meta", attrs={"name": "digiindia-student-innovation-platform"})
                    if meta_tag and meta_tag.get("content") == token:
                        verified = True
                        reason = "Meta tag verification successful!"
                    else:
                        reason = f"Meta tag 'digiindia-student-innovation-platform' with content '{token}' not found on {live_url}"

                    # Capture live html snapshot preview
                    import base64
                    snapshot_html = f"<html><body><h3>Snapshot Preview for {live_url}</h3><p>{soup.get_text()[:400]}</p></body></html>"
                    screenshot_uri = f"data:text/html;base64,{base64.b64encode(snapshot_html.encode('utf-8')).decode('utf-8')}"

                # Test robots.txt
                try:
                    robots_res = client.get(urljoin(base_domain, "/robots.txt"))
                    if robots_res.status_code == 200:
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

        except Exception as e:
            reason = f"Crawler error connecting to {live_url}: {str(e)}"

        if verified:
            verif["verificationStatus"] = "verified"
            verif["verifiedAt"] = time.time()
            verif["crawlerLog"] = reason
            verif["hasRobotsTxt"] = robots_found
            verif["hasSitemapXml"] = sitemap_found
            verif["sitemapUrlsCount"] = sitemap_urls_count
            verif["liveSnapshotURI"] = screenshot_uri

            # Update Project status & trust score
            new_trust_score = min(proj.get("trustScore", 50) + 25, 100)
            projects_repo.set(project_id, {
                "verificationStatus": "verified",
                "trustScore": new_trust_score,
                "hasRobotsTxt": robots_found,
                "hasSitemapXml": sitemap_found,
                "updatedAt": time.time()
            })
        else:
            verif["verificationStatus"] = "failed"
            verif["failureReason"] = reason

        verifications_repo.set(project_id, verif)
        return {
            "projectId": project_id,
            "verificationStatus": verif["verificationStatus"],
            "verified": verified,
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
