# DigiIndia API Generation & Fetch Logic

## 1. Overview

Purpose of DigiIndia APIs.

---

## 2. API Flow

User

↓

Dashboard

↓

API Key

↓

Store Metadata in Firestore

↓

Secret Generated

↓

Use in Applications

---

## 3. API Key Types

- Search API
- Project API
- AI API
- Organization API
- Analytics API
- Webhook API

---

## 4. API Authentication

### User APIs

Authorization: Bearer Firebase_ID_Token

### Developer APIs

X-DigiIndia-Key: di_live_xxxxxxxxx

---

## 5. Render Backend Flow

Client

↓

Render Backend

↓

Authentication Middleware

↓

Permission Check

↓

Business Service

↓

Firestore

↓

Cloudinary / AI / Brevo

↓

JSON Response

---

## 6. Base URL

Production

https://api.digiindia.org/api/v1/  --> Modify according to Render backend API Call

Development

http://localhost:8000/api/v1/

---

## 7. Search APIs

GET /api/v1/search/projects

GET /api/v1/search/students

GET /api/v1/search/organizations

GET /api/v1/search/repositories

---

## 8. Example

```http
GET /api/v1/search/projects?q=firebase

X-DigiIndia-Key: di_live_xxxxxxxxx
```

---

## 9. Response

```json
{
  "status":"success",
  "data":[]
}
```

---

## 10. API Lifecycle

Generate

↓

Use

↓

Monitor

↓

Rotate

↓

Revoke

---

## 11. Security

- HTTPS only
- Hashed API keys
- Rate limiting
- Request logging
- RBAC
- Environment variables
- No secrets in frontend

---

## 12. Conclusion

All external integrations communicate with the Render backend using authenticated API keys or Firebase ID Tokens. The backend validates permissions, executes business logic, and returns standardized JSON responses while maintaining centralized logging, security, and monitoring.