# DigiIndia – Student Innovation Platform
# API Key & API Call Handler Architecture

Version : 1.0

Status : Production Design

Architecture : Organization Level

---

# 1. Overview

The API Key & API Call Handler is the centralized gateway responsible for securely managing all external and internal API communications within the DigiIndia Student Innovation Platform.

It provides a unified interface for authentication, authorization, request validation, rate limiting, logging, monitoring, retries, and response processing.

No service communicates directly with third-party providers.

Every API request must pass through the API Call Handler.

---

# 2. Design Philosophy

Application

↓

API Manager

↓

API Call Handler

↓

Provider

↓

Response Handler

↓

Application

The API layer abstracts provider-specific implementations from the rest of the platform.

Changing providers should require minimal application changes.

---

# 3. Supported Providers

AI Providers

• Gemini API

• Grok API

• NVIDIA AI APIs

Email

• Brevo Email API

Cloud Storage

• Cloudinary API

Authentication

• Firebase Authentication

Database

• Firebase Admin SDK

Future

• GitHub API

• LinkedIn API

• ORCID API

• Google APIs

• Microsoft APIs

---

# 4. Core Responsibilities

API Key Management

Authentication

Authorization

Request Validation

Request Routing

Rate Limiting

Retry Logic

Error Handling

Logging

Monitoring

Caching

Response Validation

Audit Logging

---

# 5. Architecture

Frontend

↓

Backend Service

↓

API Call Handler

↓

Provider Client

↓

External API

↓

Provider Response

↓

Response Validator

↓

Application

---

# 6. API Key Management

Every provider has its own dedicated API key.

Keys are never shared across services.

Each key has

Provider

Purpose

Environment

Status

Creation Date

Last Rotation

Expiration

Permissions

---

# 7. API Key Storage

API keys must never be stored in

Git Repository

Frontend

JavaScript

HTML

Firestore

Cloudinary

Logs

API keys are stored only in

Firebase Secret Manager (Recommended)

or

Local .env (Development)

---

# 8. Environment Variables

GEMINI_API_KEY

GROK_API_KEY

NVIDIA_API_KEY

BREVO_API_KEY

CLOUDINARY_API_KEY

CLOUDINARY_API_SECRET

FIREBASE_PRIVATE_KEY

JWT_SECRET

---

# 9. API Key Rotation

Every API key should support rotation.

Old Key

↓

New Key

↓

Validation

↓

Deployment

↓

Old Key Revoked

Rotation should occur

Regularly

Immediately after suspected compromise

After provider recommendations

---

# 10. Request Lifecycle

Application

↓

Authentication

↓

Permission Check

↓

Validate Payload

↓

Rate Limit Check

↓

Provider Selection

↓

HTTP Request

↓

Receive Response

↓

Validate Response

↓

Store Logs

↓

Return Response

---

# 11. API Request Object

Every request contains

Provider

Endpoint

Method

Headers

Authentication

Payload

Timeout

Retry Policy

Correlation ID

---

# 12. Response Object

Status Code

Headers

Response Body

Provider

Latency

Timestamp

Request ID

Retry Count

---

# 13. Authentication

API Key

Bearer Token

OAuth

Firebase JWT

Signed Requests

Provider Specific Authentication

---

# 14. Authorization

Every backend service has permissions.

Student Service

AI Service

Notification Service

Security Service

Project Service

Analytics Service

Only authorized services can call specific providers.

---

# 15. Request Validation

Validate

Headers

Payload

Authentication

Required Fields

File Size

URL Format

Email

Phone Number

Project URL

---

# 16. Timeout Policy

AI Requests

60 Seconds

Cloudinary

30 Seconds

Brevo

15 Seconds

GitHub

30 Seconds

Custom

Configurable

---

# 17. Retry Policy

Retry only transient failures.

Retry

1

↓

2 Seconds

Retry

2

↓

5 Seconds

Retry

3

↓

15 Seconds

Retry

4

↓

60 Seconds

Maximum Retry

4

Do not retry

Authentication Errors

Permission Errors

Invalid Requests

---

# 18. Rate Limiting

Per User

Per Provider

Per Endpoint

Per API Key

Examples

AI

30 Requests/Minute

Email

10 Requests/Minute

Cloudinary Upload

20 Requests/Minute

Authentication

10 Requests/Minute

---

# 19. Provider Routing

AI Request

↓

AI Router

↓

Gemini

↓

Grok

↓

NVIDIA

↓

Fallback Provider

Email Request

↓

Brevo

Storage Request

↓

Cloudinary

Authentication

↓

Firebase

---

# 20. AI Routing Strategy

Repository Analysis

Gemini

Code Reasoning

Grok

Vision Processing

NVIDIA

Fallback

Configured Secondary Provider

---

# 21. Cloudinary Handler

Upload

Delete

Rename

Generate Signed URL

Folder Management

Metadata Update

Temporary Storage

Cleanup

---

# 22. Brevo Handler

Send Email

Template Email

Transactional Email

Password Reset

Verification Email

Security Alert

Webhook Processing

Delivery Tracking

---

# 23. Firebase Handler

Verify JWT

Create User

Delete User

Update Claims

Firestore Access

Authentication

---

# 24. Logging

Every API request stores

Provider

Endpoint

Latency

Request Size

Response Size

Status

User

Timestamp

Correlation ID

---

# 25. Audit Logging

Sensitive operations

API Key Rotation

Authentication Failure

Permission Denied

Security Alerts

Admin Requests

Configuration Changes

---

# 26. Error Handling

Every provider error is converted into a standard platform error.

Example

API-1001

Authentication Failed

API-1002

Permission Denied

API-1003

Invalid Payload

API-1004

Rate Limit Exceeded

API-1005

Provider Timeout

API-1006

Provider Unavailable

API-1007

Response Validation Failed

API-1008

API Key Missing

---

# 27. Response Validation

Validate

Status Code

JSON Structure

Required Fields

Data Types

Signature (if applicable)

Unexpected responses are rejected and logged.

---

# 28. Monitoring

Monitor

Provider Availability

Average Response Time

Error Rate

Retry Rate

Rate Limit Usage

API Key Usage

Failed Requests

Daily Requests

Monthly Requests

---

# 29. Firestore Collections

apiProviders

apiKeys

apiUsage

apiLogs

apiErrors

apiRateLimits

apiConfigurations

apiMetrics

---

# 30. apiKeys Collection

Fields

provider

environment

status

createdAt

lastRotated

expiresAt

permissions

owner

description

Note

Actual secrets are stored in Firebase Secret Manager or local `.env` during development. Firestore stores only metadata and management information.

---

# 31. apiUsage Collection

Fields

provider

endpoint

requestCount

successCount

failureCount

averageLatency

lastUsed

---

# 32. Folder Structure

functions/

└── api/

    ├── manager.py

    ├── router.py

    ├── request.py

    ├── response.py

    ├── validator.py

    ├── rate_limit.py

    ├── retry.py

    ├── cache.py

    ├── logger.py

    ├── monitoring.py

    ├── security.py

    ├── providers/

    │   ├── gemini.py

    │   ├── grok.py

    │   ├── nvidia.py

    │   ├── brevo.py

    │   ├── cloudinary.py

    │   └── firebase.py

    └── utils.py

---

# 33. Security Best Practices

Never expose API keys to the frontend.

Use HTTPS for all API communication.

Store secrets securely.

Rotate API keys periodically.

Validate every request and response.

Apply least-privilege access.

Mask sensitive values in logs.

Generate audit logs for privileged operations.

Implement rate limiting for every provider.

Use correlation IDs for tracing requests.

---

# 34. Future Enhancements

API Gateway Dashboard

Real-Time Usage Analytics

Automatic Key Rotation

Provider Health Checks

Circuit Breaker Pattern

Distributed Request Queue

Request Caching

Multi-Region Failover

Dynamic Provider Selection

Cost Optimization Engine

---

# 35. Architecture Principles

The API Call Handler is the single gateway for all external integrations.

Business services must never communicate directly with third-party providers.

Secrets are isolated from application logic.

Every request is authenticated, validated, logged, and monitored.

Provider-specific implementations remain modular, allowing services such as AI providers, Cloudinary, Brevo, and Firebase to be replaced or extended with minimal impact on the rest of the DigiIndia platform.

This architecture ensures security, maintainability, scalability, and consistent communication across all external APIs.