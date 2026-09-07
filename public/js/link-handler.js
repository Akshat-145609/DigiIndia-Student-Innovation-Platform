/**
 * DigiIndia Universal Dynamic Link Handler (link-handler.js)
 * Automatically transforms all outbound <a href="..."> elements to pass through
 * the active domain security redirect gateway:
 * {activeDomainPrefix}/api/v1/search/redirect?url={targetUrl}
 * 
 * Works seamlessly across:
 * 1. Firebase Hosting: https://digiindia-studentcollaboration.web.app
 * 2. Render Node.js Gateway: https://digiindia-student-innovation-platform-2.onrender.com
 * 3. Render Python Backend: https://digiindia-student-platform.onrender.com
 */

(function () {
    "use strict";

    // Known production domain bases
    var DOMAINS = {
        FIREBASE: "https://digiindia-studentcollaboration.web.app",
        RENDER_NODE: "https://digiindia-student-innovation-platform-2.onrender.com",
        RENDER_PYTHON: "https://digiindia-student-platform.onrender.com"
    };

    /**
     * Resolves the active domain redirect prefix based on current window location
     */
    function getActiveRedirectPrefix() {
        if (typeof window === "undefined" || !window.location) {
            return DOMAINS.RENDER_NODE + "/api/v1/search/redirect?url=";
        }

        var host = window.location.hostname || "";
        var origin = window.location.origin || "";

        if (host.includes("web.app") || host.includes("firebaseapp.com")) {
            return DOMAINS.FIREBASE + "/api/v1/search/redirect?url=";
        }
        if (host.includes("digiindia-student-innovation-platform-2.onrender.com")) {
            return DOMAINS.RENDER_NODE + "/api/v1/search/redirect?url=";
        }
        if (host.includes("digiindia-student-platform.onrender.com")) {
            return DOMAINS.RENDER_PYTHON + "/api/v1/search/redirect?url=";
        }

        // Generic / Localhost fallback
        return origin + "/api/v1/search/redirect?url=";
    }

    /**
     * Checks if a target URL is an outbound/external link
     */
    function isExternalUrl(url) {
        if (!url || typeof url !== "string") return false;
        var trimmed = url.trim();

        // Skip if currently on redirect interstitial page
        if (typeof window !== "undefined" && window.location && (window.location.pathname.includes("redirect") || window.location.pathname.includes("redirect.html"))) {
            return false;
        }

        // Skip internal/hash/javascript protocols
        if (
            trimmed.startsWith("#") ||
            trimmed.startsWith("javascript:") ||
            trimmed.startsWith("mailto:") ||
            trimmed.startsWith("tel:") ||
            trimmed.startsWith("blob:") ||
            trimmed.startsWith("data:")
        ) {
            return false;
        }

        // Skip already-redirected URLs
        if (trimmed.includes("/api/v1/search/redirect?url=") || trimmed.includes("/search/redirect?url=")) {
            return false;
        }

        // Check if external http/https
        if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            try {
                var targetHost = new URL(trimmed).hostname;
                var currentHost = window.location.hostname;
                // Treat as external if different from current host
                return targetHost !== currentHost;
            } catch (e) {
                return true;
            }
        }

        return false;
    }

    /**
     * Transforms an external URL with the active domain redirect formula
     */
    function wrapRedirectUrl(targetUrl) {
        if (!isExternalUrl(targetUrl)) return targetUrl;
        var prefix = getActiveRedirectPrefix();
        return prefix + encodeURIComponent(targetUrl.trim());
    }

    /**
     * Scans and updates an anchor element
     */
    function transformAnchor(a) {
        if (!a || a.nodeType !== 1 || a.tagName.toUpperCase() !== "A") return;
        if (a.getAttribute("data-redirect-processed") === "true" || a.getAttribute("data-no-redirect") === "true" || a.id === "proceedBtn") return;

        var rawHref = a.getAttribute("href");
        if (!rawHref) return;

        if (isExternalUrl(rawHref)) {
            var wrapped = wrapRedirectUrl(rawHref);
            a.setAttribute("href", wrapped);
            a.setAttribute("data-original-href", rawHref);
            a.setAttribute("data-redirect-processed", "true");

            // Ensure secure target attributes
            if (!a.getAttribute("target")) {
                a.setAttribute("target", "_blank");
            }
            var rel = a.getAttribute("rel") || "";
            if (!rel.includes("noopener")) rel += " noopener";
            if (!rel.includes("noreferrer")) rel += " noreferrer";
            a.setAttribute("rel", rel.trim());
        }
    }

    /**
     * Processes all links inside a container or whole document
     */
    function processAllLinks(rootNode) {
        var context = rootNode || document;
        if (!context || !context.querySelectorAll) return;

        var links = context.querySelectorAll("a[href]");
        for (var i = 0; i < links.length; i++) {
            transformAnchor(links[i]);
        }
    }

    // Set up MutationObserver to automatically catch dynamically rendered links
    function initObserver() {
        if (typeof MutationObserver === "undefined" || !document.documentElement) return;

        var observer = new MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                var mut = mutations[i];
                if (mut.type === "childList" && mut.addedNodes.length > 0) {
                    for (var j = 0; j < mut.addedNodes.length; j++) {
                        var node = mut.addedNodes[j];
                        if (node.nodeType === 1) {
                            if (node.tagName && node.tagName.toUpperCase() === "A") {
                                transformAnchor(node);
                            }
                            processAllLinks(node);
                        }
                    }
                } else if (mut.type === "attributes" && mut.attributeName === "href") {
                    transformAnchor(mut.target);
                }
            }
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["href"]
        });
    }

    // Global capture-phase click listener to intercept clicks on dynamic links
    function initClickListener() {
        document.addEventListener(
            "click",
            function (e) {
                var target = e.target;
                while (target && target.tagName !== "A" && target !== document.body) {
                    target = target.parentElement;
                }

                if (target && target.tagName === "A") {
                    var href = target.getAttribute("href");
                    if (href && isExternalUrl(href)) {
                        var wrapped = wrapRedirectUrl(href);
                        target.setAttribute("href", wrapped);
                        target.setAttribute("data-redirect-processed", "true");
                    }
                }
            },
            true
        );
    }

    // Initialize as soon as possible
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            processAllLinks(document);
            initObserver();
            initClickListener();
        });
    } else {
        processAllLinks(document);
        initObserver();
        initClickListener();
    }

    // Predefined regex and security suite for quick client evaluation
    var RAW_IP_REGEX = /^(?:https?:\/\/)?(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:[\/?#]|$)/i;
    var SUSPICIOUS_TLDS = [
        '.xyz', '.top', '.tk', '.ml', '.ga', '.cf', '.gq', '.buzz', '.fit', '.rest',
        '.work', '.click', '.link', '.stream', '.cam', '.live', '.loan', '.racing',
        '.surf', '.monster', '.icu', '.sbs', '.cfd', '.lat', '.quest', '.beauty'
    ];
    var TARGET_BRANDS = [
        'paypal', 'google', 'microsoft', 'apple', 'netflix', 'facebook',
        'instagram', 'amazon', 'bank', 'sbi', 'hdfc', 'icici', 'aadhaar', 'digilocker'
    ];
    var SENSITIVE_ACTIONS = [
        'login', 'signin', 'verify', 'update', 'security', 'account', 'wallet',
        'recover', 'portal', 'secure', 'auth', 'banking', 'checkpoint'
    ];
    var DANGEROUS_EXTENSIONS = [
        '.exe', '.scr', '.bat', '.cmd', '.vbs', '.ps1', '.msi', '.jar', '.apk', '.dmg', '.iso', '.zip', '.rar', '.7z'
    ];
    var TUNNEL_DOMAINS = [
        'ngrok-free.app', 'ngrok.io', 'loca.lt', 'trycloudflare.com', 'serveo.net', 'pagekite.me'
    ];

    function quickSecurityCheck(rawUrl) {
        if (!rawUrl || typeof rawUrl !== 'string') {
            return { isSuspicious: true, reasons: ['Invalid destination URL'], riskScore: 100, riskLevel: 'HIGH' };
        }
        var trimmed = rawUrl.trim();
        var reasons = [];
        var riskScore = 0;

        if (trimmed.includes('suspicious=true')) {
            reasons.push('Triggered by security test parameter flag');
            riskScore += 80;
        }
        if (trimmed.startsWith('javascript:') || trimmed.startsWith('data:') || trimmed.startsWith('vbscript:')) {
            reasons.push('Dangerous script pseudo-protocol detected');
            riskScore += 100;
        }
        if (trimmed.includes('@')) {
            reasons.push('User-info / credential obfuscation symbol (@) in URL');
            riskScore += 50;
        }
        if (RAW_IP_REGEX.test(trimmed)) {
            reasons.push('Direct raw IP address destination');
            riskScore += 65;
        }

        var parsed;
        try {
            parsed = new URL(trimmed.startsWith('http') ? trimmed : 'https://' + trimmed);
        } catch (e) {
            return { isSuspicious: true, reasons: ['Malformed destination URL'], riskScore: 90, riskLevel: 'HIGH' };
        }

        var hostname = (parsed.hostname || '').toLowerCase();
        var pathname = (parsed.pathname || '').toLowerCase();

        for (var i = 0; i < SUSPICIOUS_TLDS.length; i++) {
            if (hostname.endsWith(SUSPICIOUS_TLDS[i])) {
                reasons.push('High-abuse Top-Level Domain: ' + SUSPICIOUS_TLDS[i]);
                riskScore += 45;
                break;
            }
        }

        for (var j = 0; j < TUNNEL_DOMAINS.length; j++) {
            if (hostname.includes(TUNNEL_DOMAINS[j])) {
                reasons.push('Public tunnel service: ' + TUNNEL_DOMAINS[j]);
                riskScore += 40;
                break;
            }
        }

        for (var k = 0; k < TARGET_BRANDS.length; k++) {
            var brand = TARGET_BRANDS[k];
            if (hostname.includes(brand) && !hostname.endsWith(brand + '.com') && !hostname.endsWith(brand + '.org') && !hostname.endsWith(brand + '.gov.in')) {
                for (var l = 0; l < SENSITIVE_ACTIONS.length; l++) {
                    var action = SENSITIVE_ACTIONS[l];
                    if (hostname.includes(action) || pathname.includes(action)) {
                        reasons.push('Phishing heuristic: Brand ' + brand + ' combined with ' + action);
                        riskScore += 60;
                        break;
                    }
                }
            }
        }

        for (var m = 0; m < DANGEROUS_EXTENSIONS.length; m++) {
            if (pathname.endsWith(DANGEROUS_EXTENSIONS[m])) {
                reasons.push('Direct executable binary download: ' + DANGEROUS_EXTENSIONS[m]);
                riskScore += 55;
                break;
            }
        }

        var isSuspicious = riskScore >= 40 || reasons.length > 0;
        var riskLevel = riskScore >= 70 ? 'CRITICAL' : (riskScore >= 40 ? 'HIGH' : 'SAFE');
        return { isSuspicious: isSuspicious, reasons: reasons, riskScore: riskScore, riskLevel: riskLevel, hostname: hostname };
    }

    function isSuspiciousUrl(rawUrl) {
        return quickSecurityCheck(rawUrl).isSuspicious;
    }

    // Expose API on window for programmatic usage
    window.LinkHandler = {
        wrapUrl: wrapRedirectUrl,
        isExternal: isExternalUrl,
        quickSecurityCheck: quickSecurityCheck,
        isSuspiciousUrl: isSuspiciousUrl,
        processAllLinks: function (node) {
            processAllLinks(node || document);
        },
        getActiveRedirectPrefix: getActiveRedirectPrefix,
        DOMAINS: DOMAINS
    };

    console.log("[DigiIndia LinkHandler] Active redirect prefix initialized:", getActiveRedirectPrefix());
})();
