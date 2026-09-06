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

    // Expose API on window for programmatic usage
    window.LinkHandler = {
        wrapUrl: wrapRedirectUrl,
        isExternal: isExternalUrl,
        processAllLinks: function (node) {
            processAllLinks(node || document);
        },
        getActiveRedirectPrefix: getActiveRedirectPrefix,
        DOMAINS: DOMAINS
    };

    console.log("[DigiIndia LinkHandler] Active redirect prefix initialized:", getActiveRedirectPrefix());
})();
