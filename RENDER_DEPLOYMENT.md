# DigiIndia – Render Deployment Guide

This guide provides step-by-step instructions for deploying the **DigiIndia Student Innovation Platform** (FastAPI Backend + HTML5/JS Frontend) to **Render**.

---

## 1. Overview & Architecture

- **Backend**: Python FastAPI mounted with CORS middleware, Firebase Admin SDK, Cloudinary Asset Manager, Brevo REST Email API, and AI Provider Gateway (Gemini, Grok, NVIDIA, OpenAI).
- **Frontend**: Glassmorphic SPA served via FastAPI static file handler or Render Static Site.
- **Port Handling**: Render dynamically assigns a `$PORT` environment variable.

---

## 2. Deploying Backend Web Service on Render

### Step 1: Create a New Web Service
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub / GitLab repository containing `DigiIndia-Student-Innovation-Platform`.

### Step 2: Configure Service Settings

| Setting | Value |
| :--- | :--- |
| **Name** | `digiindia-backend` |
| **Region** | Choose nearest (e.g., Singapore / Frankfurt) |
| **Branch** | `main` |
| **Root Directory** | Leave blank or specify `./` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r functions/requirements.txt` |
| **Start Command** | `cd functions && uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

## 3. Environment Variables Configuration

In your Render Web Service dashboard, navigate to **Environment** and add the following keys from `functions/.env`:

```env
APP_NAME=DigiIndia
APP_ENV=production
APP_DEBUG=False
APP_URL=https://digiindia-backend.onrender.com
FRONTEND_URL=https://digiindia-backend.onrender.com

JWT_SECRET=digi-india-881238-17136031-lucky-project-222594960207
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Admin Credentials
ADMIN_NAME=Super Administrator
ADMIN_EMAIL=its.akshatnetworkhub23@gmail.com
ADMIN_PASSWORD=Admin@987

# Firebase Client
FIREBASE_API_KEY=AIzaSyBZ_gMmcW5aWMZ6o5dvHGxmGaHZav0Jdhk
FIREBASE_AUTH_DOMAIN=digiindia-studentcollaboration.firebaseapp.com
FIREBASE_PROJECT_ID=digiindia-studentcollaboration
FIREBASE_STORAGE_BUCKET=digiindia-studentcollaboration.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=222594960207
FIREBASE_APP_ID=1:222594960207:web:90d84459f219b66c21933a
FIRESTORE_DATABASE=(default)

# Cloudinary
CLOUDINARY_CLOUD_NAME=kl31i7xd
CLOUDINARY_API_KEY=754346356315531
CLOUDINARY_API_SECRET=437tWEzY-6K5UUy2E_H7tz15AZs

# Brevo Email API (REST)
BREVO_API_KEY=xkeysib-YOUR_BREVO_API_KEY_HERE
BREVO_SENDER_NAME=DigiIndia-StudentInnovationPlatform
BREVO_SENDER_EMAIL=akshatpsd2005@gmail.com
OTP_EXPIRY_MINUTES=5

# AI Provider Keys
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
GROK_API_KEY=YOUR_GROK_API_KEY_HERE
NVIDIA_API_KEY=YOUR_NVIDIA_API_KEY_HERE
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE


# Security
ENCRYPTION_KEY=Q2F4eTlpN3dRZk9mQ2x6b1FhTWx0Vm1XcE1hV1Z4S1l0V2JvZ0lqTQ==
PASSWORD_PEPPER=hGhdbw8FdCjWuqRFlF3EyY5VohMf3Thvof864WMrBKo
CORS_ALLOWED_ORIGINS=*

# Feature Flags
ENABLE_AI=true
ENABLE_EMAIL=true
ENABLE_ANALYTICS=true
ENABLE_NOTIFICATIONS=true
```

---

## 4. Verification After Render Deployment

Once Render completes the build:
1. Open `https://your-service.onrender.com/api/v1/health` to verify response `{"status":"healthy"}`.
2. Open `https://your-service.onrender.com/index.html` to test the live Web Application.
3. Access `https://your-service.onrender.com/docs` to test interactive Swagger OpenAPI documentation.
