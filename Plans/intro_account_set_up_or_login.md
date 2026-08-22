Below is an **Antigravity-first implementation plan** for your project.

> **Project Name (Firebase):** DigiIndia-StudentCollaboration
>
> **Product Name:** DigiIndia – Student Innovation Platform

Since you've mentioned **workspace setup is already done**, this plan starts from the point where Antigravity begins generating the application.

---

# DigiIndia - Student Innovation Platform

## Antigravity Implementation Plan

---

# Phase 1 — Project Foundation

Antigravity should generate:

```
Landing Website
Authentication System
Student Registration Wizard
Student Login
Dashboard
Settings
Legal Center
Documentation
Firebase Integration
Cloudinary Integration
```

Technology

```
Frontend
React + Tailwind

Backend
Firebase

Authentication
Firebase Auth

Database
Cloud Firestore

Storage
Cloudinary

Hosting
Firebase Hosting

OTP
Firebase Authentication

Email Verification
Firebase Email Action Links

OCR
Google ML Kit / Gemini Vision API

Camera
MediaDevices API

Security
Firebase Security Rules
```

---

# Phase 2 — Homepage

Homepage Sections

```
Navbar

Logo

Home

Documentation

Legal Center

Login

Create Account
```

---

Hero Section

```
DigiIndia

Student Innovation Platform

One Digital Identity for Every Student
```

Buttons

```
Create Account

Login
```

---

Overview Section

Small concise introduction

Example

> DigiIndia Student Innovation Platform enables verified students to collaborate, build innovation projects, showcase achievements, participate in hackathons, and maintain a secure academic identity across institutions.

---

Documentation

Links

```
Getting Started

Features

Student Guide

FAQ
```

---

Legal Center

```
Privacy Policy

Terms

Cookie Policy

Data Retention

Contact
```

---

# Phase 3 — Authentication Module

Two options

```
Create Account

Login
```

---

# Phase 4 — Student Registration Wizard

Instead of one long form

Antigravity should generate a

**Stepper Registration**

```
Step 1

Student Verification

↓

Step 2

College Verification

↓

Step 3

Contact Information

↓

Step 4

Security Email

↓

Step 5

Social Profiles

↓

Step 6

Password

↓

Finish
```

---

# STEP 1

Student Verification

Title

```
Verify Your Identity
```

Two cards

```
ABC ID

OR

Aadhaar Card
```

Upload Control

```
Drag and Drop

Browse Files
```

Accepted

```
jpg

png

pdf
```

---

OCR Flow

If ABC uploaded

Extract

```
Student Name

ABC ID
```

If Aadhaar uploaded

Extract

```
Student Name

Aadhaar Number
```

If both uploaded

Validation

```
Compare Names

Match?

Yes

Proceed

No

Show Error
```

---

Store

```
Cloudinary

folder

/private/student-verification
```

Save URL

```
Firestore
```

Document Metadata

```
uploadTime

verificationStatus

ocrResult

cloudinaryURL
```

---

Buttons

```
Back

Next
```

---

# STEP 2

College Verification

Upload

```
College ID Card

School ID Card
```

Live Camera

```
Take Selfie

Preview

Retake
```

Validation

```
Face visible

No blur

One person only
```

Upload

Cloudinary

```
private/student-id

private/selfie
```

Store URLs

Firestore

---

# STEP 3

Other Details

Fields

```
WhatsApp Number

Contact Number

Primary Email
```

Checkbox

```
Same as WhatsApp
```

OTP

Firebase Phone Authentication

```
Send OTP

Verify OTP
```

Email

Firebase Email Verification

```
Send Verification

Verified
```

---

# STEP 4

Security Email

Optional

```
Security Email
```

Verification

```
Dynamic Email Link

Verify

Continue
```

Skip

```
Configure Later
```

Dashboard Reminder

```
Security Email Missing
```

---

# STEP 5

Social Profiles

Fields

```
LinkedIn

GitHub

LeetCode

HackerRank

DPG Notes
```

Validation

Accept only proper URLs.

---

# STEP 6

Password

Fields

```
Password

Confirm Password
```

Live strength meter

```
Weak

Medium

Strong

Excellent
```

Captcha

Image Captcha

Buttons

```
Back

Create Account
```

---

# Account Creation Flow

On clicking

```
Create Account
```

Backend executes

```
Validate Form

↓

Verify OTP

↓

Verify Email

↓

Upload Documents

↓

Save Firestore

↓

Generate SPN

↓

Create Firebase User

↓

Redirect Dashboard
```

---

# SPN Generation

Requirement

```
8 Digits

Unique

Permanent

Never reused
```

Example

```
24003145

24003146

24003147
```

Recommended format

```
YY + 6 Random Digits
```

Example

```
26012345
```

Use a Firestore transaction or Cloud Function to guarantee uniqueness and avoid collisions.

---

Firestore Document

```
students

studentId

uid

spn

name

email

phone

abcId

aadhaar

college

cloudinaryLinks

socialProfiles

createdAt

status

verified
```

---

# Login Screen

Allow

```
SPN

OR

Email
```

Password

Captcha

Button

```
Login
```

Flow

```
Input

↓

Check if SPN

↓

Fetch Email

↓

Firebase Login

↓

Dashboard
```

---

# Dashboard

Sections

```
Profile

Verification Status

Innovation Projects

Collaborations

Certificates

Achievements

Hackathons

Settings

Logout
```

---

# Settings

Student can

```
Change Password

Update Contact

Add Security Email

Manage Social Links

Download Documents

Delete Account
```

---

# Cloudinary Folder Structure

```
students/

    verification/

        abc/

        aadhaar/

    college/

    selfie/

    certificates/

    innovation/
```

Use authenticated/private delivery for sensitive documents.

---

# Firebase Collections

```
students

verification

socialProfiles

securityEmails

loginHistory

notifications

projects

hackathons
```

---

# Security Rules

Firestore

```
Student can read only own document.

Student cannot modify SPN.

Only verified users can access dashboard.

Admin can read all.

Admin can update verification status.
```

Cloudinary

```
Private Upload

Signed URLs

Authenticated Delivery

Folder Restrictions
```

---

# Suggested Future Enhancements

After the MVP is complete, Antigravity can generate additional modules:

* **Admin Portal** for manual verification of uploaded documents and approval/rejection workflows.
* **Role-based access control** (Student, College, Verifier, Super Admin).
* **Institution onboarding** so colleges can verify students directly.
* **Project collaboration workspace** with teams, mentors, and repositories.
* **Innovation showcase** with public student portfolios.
* **Notification center** using Firebase Cloud Messaging.
* **Audit logs** for verification actions and security-sensitive changes.
* **AI-assisted document quality checks** (blur detection, document completeness).
* **Digital student ID card** with a QR code linked to the student's verified profile.
* **Analytics dashboard** for platform usage, registrations, and verification status.

## Notes

* Using **Cloudinary** for private document storage and **Firebase** for authentication and metadata aligns well with your goal of minimizing costs while keeping sensitive files outside Firestore.
* For **Aadhaar**, ensure compliance with applicable Indian regulations. Avoid exposing or unnecessarily processing Aadhaar numbers, encrypt sensitive identifiers where possible, and restrict access to authorized users only.
* OCR extraction should be treated as an aid; consider allowing users or administrators to review extracted fields when confidence is low.

This implementation plan provides Antigravity with a clear, modular roadmap to generate the DigiIndia Student Innovation Platform while leaving environment and workspace setup to your existing configuration.
