# DigiIndia – Student Innovation Platform
# Design Specification

Version : 1.0
Architecture : Organization Level
Frontend : HTML5 • CSS3 • Bootstrap 5 • JavaScript
Backend : Python • Node.js • Firebase Functions
Database : Cloud Firestore
Storage : Cloudinary (Authenticated Assets)
Authentication : Firebase Authentication
Mail : Brevo SMTP
AI Layer : Gemini • Grok • NVIDIA AI
OCR : Python AI Engine
Hosting : Firebase Hosting

---

# 1. Design Philosophy

The DigiIndia Student Innovation Platform is not a traditional student portal.

It is a collaborative innovation ecosystem where every verified student owns a professional digital identity, publishes projects, collaborates with other developers, and integrates their portfolio with external websites through secure APIs.

The interface follows

• Minimal Design
• Modern Design
• Material Inspired Components
• Bootstrap Responsive Layout
• Mobile First Approach
• SPA (Single Page Application)

---

# 2. Global Theme

Default Theme

Primary
#0D6EFD

Secondary
#6610F2

Success
#198754

Danger
#DC3545

Warning
#FFC107

Info
#0DCAF0

Light
#F8F9FA

Dark
#212529

Accent

Gradient

Blue → Indigo

---

# 3. Typography

Font

Poppins

Fallback

Segoe UI

Roboto

Sans-serif

Heading Weight

700

Body

500

Buttons

600

Letter Spacing

0.2px

---

# 4. Border Radius

Cards

18px

Buttons

12px

Modal

20px

Input

12px

Avatar

50%

---

# 5. Shadows

Cards

Soft Shadow

Hover

Elevated Shadow

Sidebar

Medium Shadow

Floating Buttons

Large Shadow

---

# 6. Glass Morphism

Applied To

Navbar

Sidebar

Floating Cards

Profile Header

Notifications

Search Panel

Opacity

90%

Blur

20px

---

# 7. SPA Layout

------------------------------------------------------

Navbar

------------------------------------------------------

Sidebar

|

|

|

|

Content Area

|

|

|

|

------------------------------------------------------

Bottom Navigation (Mobile Only)

------------------------------------------------------

Every Sidebar Click

↓

Load Dynamic Component

↓

No Page Refresh

---

# 8. Navbar

Contains

Logo

Global Search

Notifications

Messages

AI Assistant

Profile Avatar

Theme Toggle

Logout

Sticky

Always Visible

---

# 9. Sidebar

Bootstrap Icons

bi-person

Profile

bi-gear

Settings

bi-upload

Upload Project

bi-patch-check

Verify Project

bi-key

API Keys

bi-search

Search Projects

bi-people

Search Users

bi-diagram-3

Your Network

bi-chat-dots

Messages

bi-bell

Notifications

bi-stars

AI Assistant

bi-box-arrow-right

Logout

---

# 10. Sidebar Behaviour

Desktop

Expanded

Tablet

Collapsible

Mobile

Hidden

Open

Swipe Right

or

Hamburger

Close

Swipe Left

or

Close Button

---

# 11. Quick Action Panel

Floating Card

Contains

Upload Project

Generate API

Search

New Message

AI Chat

Create Workspace

Create Team

---

# 12. Dashboard Cards

Rounded

Gradient Header

Hover Animation

Smooth Shadow

Animated Counters

Examples

Projects

Followers

Connections

Verification

API Usage

Messages

---

# 13. Profile Design

Large Cover Image

Circular Profile Image

Verification Badge

Trust Score

SPN

College

Department

Skills

Bio

Social Links

Buttons

Visit Public Profile

Edit Profile

Share

Generate QR

---

# 14. Project Cards

Contain

Project Logo

Title

Description

Technology Stack

Repository

Live URL

Trust Score

Uploader

Organization

Verification Badge

Buttons

Visit

Repository

Follow

Connect

Save

Share

---

# 15. Search UI

Live Search

Auto Complete

Filter Chips

Sort

Newest

Popular

Verified

Trending

Institution

Technology

---

# 16. Forms

Floating Labels

Bootstrap Validation

Animated Success

AI Suggestions

Smart Autofill

Real Time Validation

---

# 17. Upload Project UI

Step Based

Repository URL

↓

Validate

↓

Extract Metadata

↓

Preview

↓

AI Analysis

↓

Submit

Progress Bar

Shown

Always

---

# 18. AI Analysis Screen

Sections

Repository Analysis

Website Analysis

Person Schema

Organization Schema

Trust Score

AI Summary

SEO Analysis

Accessibility

Performance

---

# 19. AI Cards

Markdown Renderer

Syntax Highlighting

Collapsible

Copy Button

Regenerate Button

Download Markdown

---

# 20. Verification Screen

Project Status

Pending

Verified

Rejected

Needs Review

Timeline

Submission

Crawler

Validation

Verification

---

# 21. Notifications

Slide Panel

Real Time

Categories

Security

Messages

Projects

Verification

Network

System

---

# 22. Messaging

Modern Chat

Typing Indicator

Read Receipt

File Upload

Code Snippet

Markdown

Future

Voice

Video

Screen Share

---

# 23. Network

Followers

Following

Connections

Suggested Users

Mutual Connections

Invite

---

# 24. API Keys

Table View

Cards

Copy

Regenerate

Disable

Delete

Usage Analytics

Permission Scope

Expiry

---

# 25. Settings

Accordion Layout

Sections

Account

Security

Privacy

Notifications

Appearance

Language

Developer

Danger Zone

---

# 26. Theme Engine

Light

Dark

System

High Contrast

Future

Custom Theme Builder

---

# 27. Animations

Fade

Slide

Scale

Skeleton Loader

Count Up

Lottie

Shimmer

Loading Overlay

---

# 28. Accessibility

Keyboard Navigation

Screen Reader

ARIA Labels

Focus Indicators

High Contrast

Reduced Motion

Responsive Font Scaling

---

# 29. Mobile Experience

Bottom Navigation

Gesture Support

Swipe Sidebar

Pull To Refresh

Touch Friendly Buttons

Minimum Touch Area

48px

---

# 30. Performance

Lazy Loading

Code Splitting

Image Compression

Cloudinary CDN

Firestore Cache

Debounced Search

Pagination

Infinite Scroll

---

# 31. Security UI

Sensitive Inputs Hidden

Password Strength

OTP Status

2FA Status

Session History

Login Devices

Security Alerts

---

# 32. Organization Level Architecture

Student

↓

Projects

↓

Verification

↓

AI Engine

↓

Search Engine

↓

Network

↓

API Gateway

↓

Analytics

↓

Public Profile

Every module communicates through Firestore and secured backend services.

---

# 33. Future Design Modules

Hackathons

Research Labs

Innovation Challenges

Startup Showcase

Patent Repository

Mentor Dashboard

Organization Dashboard

College Dashboard

Admin Dashboard

AI Marketplace

Skill Graph

Digital Resume Builder

Achievement Timeline

Blockchain Certificates

Open Source Collaboration Workspace

Live Pair Programming

Video Meeting

Developer Reputation System

Global Innovation Ranking

---

# Design Principles

Consistency

Accessibility

Performance

Security

Scalability

AI First

Developer Friendly

Student Focused

Mobile First

Organization Level Architecture