const getApiBaseUrl = () => {
    if (typeof CONFIG !== "undefined" && CONFIG.API_BASE_URL) {
        return CONFIG.API_BASE_URL;
    }
    const origin = window.location.origin;
    if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
        return "http://localhost:8000/api/v1";
    }
    if (origin.includes("web.app") || origin.includes("firebaseapp.com")) {
        return "https://digiindia-student-innovation-platform-2.onrender.com/api/v1";
    }
    return `${origin}/api/v1`;
};

const API = {
    getBaseUrl() {
        return getApiBaseUrl();
    },
    getToken() {
        return localStorage.getItem("digiindia_token") || "";
    },
    setToken(token) {
        localStorage.setItem("digiindia_token", token);
    },
    getUser() {
        const u = localStorage.getItem("digiindia_user");
        return u ? JSON.parse(u) : null;
    },
    setUser(user) {
        localStorage.setItem("digiindia_user", JSON.stringify(user));
    },
    clearAuth() {
        localStorage.removeItem("digiindia_token");
        localStorage.removeItem("digiindia_user");
    },
    async request(endpoint, options = {}) {
        const url = `${getApiBaseUrl()}${endpoint}`;
        const headers = options.headers || {};

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
            headers["Content-Type"] = "application/json";
        }

        options.headers = headers;

        try {
            const res = await fetch(url, options);
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                let errMsg = data.detail || data.message || `Request failed with status ${res.status}`;
                if (Array.isArray(errMsg)) {
                    errMsg = errMsg.map(e => `${e.loc ? e.loc.join('->') + ': ' : ''}${e.msg}`).join('; ');
                } else if (typeof errMsg === 'object') {
                    errMsg = JSON.stringify(errMsg);
                }
                throw new Error(errMsg);
            }

            return data;
        } catch (err) {
            console.error(`API Error [${endpoint}]:`, err);
            throw err;
        }
    },
    showToast(message, type = "info") {
        const container = document.getElementById("toast-container") || document.body;
        const toast = document.createElement("div");
        toast.className = `alert alert-${type === "error" ? "danger" : type} alert-dismissible fade show position-fixed bottom-0 end-0 m-3 z-3 shadow-lg`;
        toast.style.minWidth = "300px";
        toast.innerHTML = `
            <strong>${type === "error" ? "Error" : "Notice"}:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    },
    showCustomAlert(title, message, callback) {
        const modalId = "customAlertModal";
        let modalEl = document.getElementById(modalId);
        if (!modalEl) {
            modalEl = document.createElement("div");
            modalEl.id = modalId;
            modalEl.className = "modal fade";
            modalEl.tabIndex = -1;
            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content glass-card p-2 border-0 shadow-lg">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold text-primary" id="customAlertTitle">Alert</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="customAlertBody"></div>
                        <div class="modal-footer border-0 pt-0">
                            <button type="button" class="btn btn-gradient px-4" data-bs-dismiss="modal" id="customAlertOkBtn">OK</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);
        }
        document.getElementById("customAlertTitle").innerText = title;
        document.getElementById("customAlertBody").innerHTML = message;
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();
        if (callback) {
            const okBtn = document.getElementById("customAlertOkBtn");
            const handler = () => {
                callback();
                okBtn.removeEventListener("click", handler);
            };
            okBtn.addEventListener("click", handler);
        }
    },
    showCustomConfirm(title, message, onConfirm) {
        const modalId = "customConfirmModal";
        let modalEl = document.getElementById(modalId);
        if (!modalEl) {
            modalEl = document.createElement("div");
            modalEl.id = modalId;
            modalEl.className = "modal fade";
            modalEl.tabIndex = -1;
            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content glass-card p-3 border-0 shadow-lg">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold text-danger" id="customConfirmTitle">Confirm Action</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body py-3" id="customConfirmBody"></div>
                        <div class="modal-footer border-0 pt-0 d-flex gap-2">
                            <button type="button" class="btn btn-outline-secondary flex-grow-1" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger flex-grow-1" id="customConfirmYesBtn" data-bs-dismiss="modal">Confirm</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);
        }
        document.getElementById("customConfirmTitle").innerText = title;
        document.getElementById("customConfirmBody").innerText = message;
        
        let bsModal = bootstrap.Modal.getInstance(modalEl);
        if (!bsModal) {
            bsModal = new bootstrap.Modal(modalEl);
        }

        const yesBtn = document.getElementById("customConfirmYesBtn");
        yesBtn.onclick = () => {
            if (onConfirm) onConfirm();
        };

        bsModal.show();
    }

};

const NetworkActions = {
    async handleConnectClick(targetUID, currentState, onUpdate) {
        if (!API.getToken()) {
            API.showToast("Please log in to connect with students", "warning");
            return;
        }

        if (currentState === "PENDING_SENT") {
            API.showCustomConfirm(
                "Withdraw Connection Request",
                "Do you want to withdraw your pending connection request?",
                async () => {
                    try {
                        await API.request(`/network/connection/withdraw/${targetUID}`, { method: "POST" });
                        API.showToast("Connection request withdrawn", "info");
                        if (onUpdate) onUpdate("NONE");
                    } catch(e) { API.showToast(e.message, "error"); }
                }
            );
        } else if (currentState === "CONNECTED") {
            API.showCustomConfirm(
                "Disconnect Student",
                "Are you sure you want to disconnect from this student?",
                async () => {
                    try {
                        await API.request(`/network/connection/disconnect/${targetUID}`, { method: "DELETE" });
                        API.showToast("Disconnected successfully", "info");
                        if (onUpdate) onUpdate("NONE");
                    } catch(e) { API.showToast(e.message, "error"); }
                }
            );
        } else if (currentState === "PENDING_RECEIVED") {
            try {
                await API.request(`/network/connection/respond/${targetUID}?accept=true`, { method: "POST" });
                API.showToast("Connection request accepted!", "success");
                if (onUpdate) onUpdate("CONNECTED");
            } catch(e) { API.showToast(e.message, "error"); }
        } else {
            // State is NONE -> Send request
            try {
                await API.request(`/network/connection/request`, {
                    method: "POST",
                    body: JSON.stringify({ targetUID, message: "Let's connect on DigiIndia!" })
                });
                API.showToast("Connection request sent!", "success");
                if (onUpdate) onUpdate("PENDING_SENT");
            } catch(e) { API.showToast(e.message, "error"); }
        }
    },

    async handleFollowClick(targetUID, isFollowing, onUpdate) {
        if (!API.getToken()) {
            API.showToast("Please log in to follow students", "warning");
            return;
        }
        try {
            if (!isFollowing) {
                await API.request(`/network/follow/${targetUID}`, { method: "POST" });
                API.showToast("Following student updates!", "success");
                if (onUpdate) onUpdate(true);
            } else {
                await API.request(`/network/follow/${targetUID}`, { method: "DELETE" });
                API.showToast("Unfollowed student", "info");
                if (onUpdate) onUpdate(false);
            }
        } catch(e) { API.showToast(e.message, "error"); }
    }
};

window.API = API;
window.NetworkActions = NetworkActions;

// Auto warm-up Render backend on page load if sleeping due to inactivity
document.addEventListener("DOMContentLoaded", () => {
    try {
        fetch(`${getApiBaseUrl()}/health`).catch(() => {});
    } catch (e) {}
});
