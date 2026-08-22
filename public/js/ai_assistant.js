const DigiIndiaAI = {
    async analyzeUrl(url) {
        if (!url) return "<div class='alert alert-warning'>Please enter a valid target URL.</div>";
        try {
            const res = await API.request(`/ai/analyze-url?url=${encodeURIComponent(url)}`, { method: "POST" });
            const replyText = res.reply || res.response || (typeof res === "string" ? res : JSON.stringify(res, null, 2));
            return `
            <div class="card border-0 bg-white p-3 shadow-sm rounded-3">
                <h6 class="fw-bold text-primary mb-2"><i class="bi bi-link-45deg me-1"></i>URL Architectural Analysis Report</h6>
                <p class="small text-muted mb-2">Target URL: <code>${url}</code></p>
                <div class="small text-dark fw-medium" style="white-space: pre-wrap; line-height: 1.6;">${replyText}</div>
            </div>
            `;
        } catch (err) {
            return `<div class="alert alert-danger">Error analyzing URL: ${err.message}</div>`;
        }
    },

    async analyzeSEO(url) {
        if (!url) return "<div class='alert alert-warning'>Please enter a valid target URL.</div>";
        try {
            const res = await API.request(`/ai/analyze-seo?url=${encodeURIComponent(url)}`, { method: "POST" });
            return `
            <div class="card border-0 bg-white p-3 shadow-sm rounded-3">
                <h6 class="fw-bold text-success mb-2"><i class="bi bi-search me-1"></i>SEO & Metadata Audit Report</h6>
                <p class="small text-muted mb-2">Target URL: <code>${res.url || url}</code></p>
                <div class="mb-3">
                    <span class="fs-4 fw-bold text-success">${res.seoScore || 85}</span> <span class="small text-muted">/ 100 SEO Health Index</span>
                </div>
                <ul class="list-group list-group-flush small mb-0">
                    <li class="list-group-item d-flex justify-content-between px-0">Title Tag: <strong>${res.hasTitle ? '✓ Present' : '✗ Missing'}</strong></li>
                    <li class="list-group-item d-flex justify-content-between px-0">Meta Description: <strong>${res.hasMetaDescription ? '✓ Present' : '✗ Missing'}</strong></li>
                    <li class="list-group-item d-flex justify-content-between px-0">OpenGraph Protocol: <strong>${res.hasOpenGraph ? '✓ Configured' : '✗ Missing'}</strong></li>
                    <li class="list-group-item d-flex justify-content-between px-0">Canonical Link: <strong>${res.hasCanonical ? '✓ Configured' : '✗ Missing'}</strong></li>
                </ul>
            </div>
            `;
        } catch (err) {
            return `<div class="alert alert-danger">Error analyzing SEO: ${err.message}</div>`;
        }
    },

    async analyzeOwnershipUrl(url, verificationToken = "") {
        if (!url) return "<div class='alert alert-warning'>Please enter a valid target URL.</div>";
        try {
            const res = await API.request(`/ai/analyze-ownership-url?url=${encodeURIComponent(url)}&verification_token=${encodeURIComponent(verificationToken)}`, { method: "POST" });
            return `
            <div class="card border-0 bg-white p-3 shadow-sm rounded-3">
                <h6 class="fw-bold text-purple mb-2"><i class="bi bi-shield-check me-1"></i>Ownership Meta Tag Audit</h6>
                <p class="small text-muted mb-2">Target URL: <code>${res.targetURL}</code></p>
                <p class="mb-1">Meta Tag Found: <strong>${res.metaTagFound ? '✓ YES' : '✗ NO'}</strong></p>
                <p class="mb-0">Ownership Score: <span class="badge bg-${res.ownershipScore>=80?'success':'warning'} fs-6">${res.ownershipScore} / 100</span></p>
            </div>
            `;
        } catch (err) {
            return `<div class="alert alert-danger">Error analyzing ownership: ${err.message}</div>`;
        }
    },

    async trainFromRepo(repoUrl) {
        if (!repoUrl) return "<div class='alert alert-warning'>Please enter a valid GitHub Repository URL.</div>";
        try {
            const res = await API.request(`/ai/train-url`, { method: "POST", body: JSON.stringify({ url: repoUrl }) });
            return `
            <div class="alert alert-success border-0 shadow-sm p-3 rounded-3">
                <h6 class="fw-bold text-success mb-2"><i class="bi bi-cpu me-1"></i>Multi-Stage AI Crawler Complete!</h6>
                <p class="small mb-1">Knowledge Record ID: <code>${res.knowledgeId}</code></p>
                <p class="small mb-0">Sub-pages crawled & ingested: <strong>${res.subPagesCrawled || 1}</strong></p>
            </div>
            `;
        } catch (err) {
            return `<div class="alert alert-danger">Error training AI model: ${err.message}</div>`;
        }
    }
};
