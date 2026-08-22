const CONFIG = {
    API_BASE_URL: window.location.origin.includes("localhost") 
        ? "http://localhost:8000/api/v1" 
        : "/api/v1",
    APP_NAME: "DigiIndia",
    FIREBASE_CONFIG: {
        apiKey: "AIzaSyBZ_gMmcW5aWMZ6o5dvHGxmGaHZav0Jdhk",
        authDomain: "digiindia-studentcollaboration.firebaseapp.com",
        projectId: "digiindia-studentcollaboration",
        storageBucket: "digiindia-studentcollaboration.firebasestorage.app",
        messagingSenderId: "222594960207",
        appId: "1:222594960207:web:90d84459f219b66c21933a"
    }
};
