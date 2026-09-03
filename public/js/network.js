// DigiIndia Network & Social Collaboration Module
// Exports NetworkActions and connects with DigiIndia API Gateway

(function() {
    if (typeof window !== "undefined") {
        if (!window.NetworkActions && typeof NetworkActions !== "undefined") {
            window.NetworkActions = NetworkActions;
        }
    }
})();
