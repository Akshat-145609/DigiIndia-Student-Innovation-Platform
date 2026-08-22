```js
<script type="module">
  // Import the functions you need from the SDKs you need
  import { initializeApp } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-app.js";
  import { getAnalytics } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-analytics.js";
  // TODO: Add SDKs for Firebase products that you want to use
  // https://firebase.google.com/docs/web/setup#available-libraries

  // Your web app's Firebase configuration
  // For Firebase JS SDK v7.20.0 and later, measurementId is optional
  const firebaseConfig = {
    apiKey: "AIzaSyBZ_gMmcW5aWMZ6o5dvHGxmGaHZav0Jdhk",
    authDomain: "digiindia-studentcollaboration.firebaseapp.com",
    projectId: "digiindia-studentcollaboration",
    storageBucket: "digiindia-studentcollaboration.firebasestorage.app",
    messagingSenderId: "222594960207",
    appId: "1:222594960207:web:90d84459f219b66c21933a",
    measurementId: "G-H0C7WX23VF"
  };

  // Initialize Firebase
  const app = initializeApp(firebaseConfig);
  const analytics = getAnalytics(app);
</script>
```