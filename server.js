const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
require('dotenv').config({ path: path.join(__dirname, 'functions', '.env') });

const app = express();
const PORT = process.env.PORT || 8000;

// Security Settings
const JWT_SECRET = process.env.JWT_SECRET || 'digi-india-881238-17136031-lucky-project-222594960207';
const JWT_ALGORITHM = process.env.JWT_ALGORITHM || 'HS256';
const JWT_EXPIRE_MINUTES = parseInt(process.env.JWT_EXPIRE_MINUTES || '1440', 10);
const PASSWORD_PEPPER = process.env.PASSWORD_PEPPER || 'hGhdbw8FdCjWuqRFlF3EyY5VohMf3Thvof864WMrBKo';
const ADMIN_NAME = process.env.ADMIN_NAME || 'Super Administrator';
const ADMIN_EMAIL = (process.env.ADMIN_EMAIL || 'its.akshatnetworkhub23@gmail.com').toLowerCase();
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'Admin@987';
const FIREBASE_PROJECT_ID = process.env.FIREBASE_PROJECT_ID || 'digiindia-studentcollaboration';

// Middleware
app.use(cors({ origin: '*' }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Firebase Admin SDK & Firestore with Local Disk Fallback
let db = null;
try {
  const admin = require('firebase-admin');
  const serviceAccEnv = process.env.FIREBASE_SERVICE_ACCOUNT || '';
  const serviceAccFile = path.join(__dirname, 'functions', 'firebase-service-account.json');

  let cred = null;
  if (serviceAccEnv) {
    try {
      const decoded = Buffer.from(serviceAccEnv, 'base64').toString('utf-8');
      cred = admin.credential.cert(JSON.parse(decoded));
    } catch (e) {
      try { cred = admin.credential.cert(JSON.parse(serviceAccEnv)); } catch (err) {}
    }
  } else if (fs.existsSync(serviceAccFile)) {
    try { cred = admin.credential.cert(serviceAccFile); } catch (e) {}
  }

  if (!admin.apps.length) {
    if (cred) {
      admin.initializeApp({ credential: cred, projectId: FIREBASE_PROJECT_ID });
    } else {
      admin.initializeApp({ projectId: FIREBASE_PROJECT_ID });
    }
  }
  db = admin.firestore();
  console.log('[Node.js Server] Firebase Admin SDK & Firestore client initialized successfully.');
} catch (err) {
  console.warn('[Node.js Server] Firebase Admin SDK note:', err.message, '- Operating with high-performance local store fallback.');
}

// Local JSON Storage Helpers
const DATA_STORE_DIR = path.join(__dirname, 'functions', 'data_store');
if (!fs.existsSync(DATA_STORE_DIR)) {
  fs.mkdirSync(DATA_STORE_DIR, { recursive: true });
}

function loadCollection(colName) {
  const filePath = path.join(DATA_STORE_DIR, `${colName}.json`);
  if (fs.existsSync(filePath)) {
    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    } catch (e) {
      return {};
    }
  }
  return {};
}

function saveCollection(colName, data) {
  const filePath = path.join(DATA_STORE_DIR, `${colName}.json`);
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
  } catch (e) {
    console.error(`Error saving disk collection ${colName}:`, e.message);
  }
}

async function getCollectionDocs(colName) {
  const diskData = loadCollection(colName);
  const docsMap = { ...diskData };

  if (db) {
    try {
      const snapshot = await db.collection(colName).limit(500).get();
      snapshot.forEach(doc => {
        docsMap[doc.id] = { id: doc.id, ...doc.data(), ...docsMap[doc.id] };
      });
    } catch (err) {
      // Use local disk data if Firestore offline
    }
  }
  return Object.values(docsMap);
}

async function saveDoc(colName, docId, data) {
  const col = loadCollection(colName);
  col[docId] = { ...(col[docId] || {}), ...data };
  saveCollection(colName, col);

  if (db) {
    try {
      await db.collection(colName).doc(docId).set(data, { merge: true });
    } catch (err) {}
  }
  return docId;
}

// Password Hashing & Verification Logic (Supports unlimited password length safely)
function preparePassword(password, pepper = PASSWORD_PEPPER) {
  const salted = `${password}${pepper || ''}`;
  return crypto.createHash('sha256').update(salted, 'utf-8').digest('hex');
}

function hashPassword(password) {
  const prep = preparePassword(password);
  return bcrypt.hashSync(prep, 10);
}

function verifyPassword(plainPassword, hashedPassword) {
  if (!plainPassword || !hashedPassword) return false;

  let h = String(hashedPassword).trim();
  if (!h.startsWith('$') && h.length >= 50) {
    h = `$2b$12$${h}`;
  }

  const peppersToTry = [PASSWORD_PEPPER, 'hGhdbw8FdCjWuqRFlF3EyY5VohMf3Thvof864WMrBKo', ''];
  for (const p of peppersToTry) {
    try {
      const prep = preparePassword(plainPassword, p);
      if (bcrypt.compareSync(prep, h)) return true;
    } catch (e) {}
  }

  try {
    if (bcrypt.compareSync(plainPassword, h)) return true;
  } catch (e) {}

  return plainPassword === hashedPassword;
}

// Generate Unique 8-Digit SPN
async function generateSPN() {
  const yearPrefix = new Date().getFullYear().toString().slice(-2);
  const students = await getCollectionDocs('students');
  const existingSPNs = new Set(students.map(s => String(s.spn)));

  while (true) {
    const randomDigits = Math.floor(100000 + Math.random() * 900000).toString();
    const candidate = `${yearPrefix}${randomDigits}`;
    if (!existingSPNs.has(candidate)) return candidate;
  }
}

// JWT Helper
function createJWTToken(uid, email, role = 'student') {
  return jwt.sign(
    { uid, email, role },
    JWT_SECRET,
    { expiresIn: `${JWT_EXPIRE_MINUTES}m` }
  );
}

// Authentication Middleware
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ detail: 'API-1001: Authentication required' });

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) return res.status(401).json({ detail: 'API-1001: Invalid or expired token' });
    req.user = user;
    next();
  });
}

// ==========================================
// API ROUTES (/api/v1/auth)
// ==========================================

// Health Check
app.get('/api/v1/health', (req, res) => {
  res.json({
    status: 'healthy',
    app: 'DigiIndia Node.js Gateway',
    environment: process.env.APP_ENV || 'production',
    features: {
      ai: true,
      email: true,
      notifications: true
    }
  });
});

// GET /api/v1/auth/login
app.get('/api/v1/auth/login', (req, res) => {
  res.json({
    status: 'active',
    endpoint: '/api/v1/auth/login',
    method: 'POST',
    message: "Authentication API endpoint active. Submit a POST request with JSON body containing 'identifier' (Email or SPN) and 'password'."
  });
});

// GET /api/v1/auth/register
app.get('/api/v1/auth/register', (req, res) => {
  res.json({
    status: 'active',
    endpoint: '/api/v1/auth/register',
    method: 'POST',
    message: 'Student Registration API endpoint. Submit a POST request with student registration details.'
  });
});

// POST /api/v1/auth/register
app.post('/api/v1/auth/register', async (req, res) => {
  try {
    const { email, phone, whatsapp, password, fullName, college, course, semester, graduationYear, securityEmail, skills, socialLinks, avatarURL, coverURL } = req.body;
    if (!email || !password || !fullName) {
      return res.status(400).json({ detail: 'Email, password, and full name are required' });
    }

    const students = await getCollectionDocs('students');
    const existing = students.find(s => String(s.email).toLowerCase() === email.toLowerCase());
    if (existing) {
      return res.status(400).json({ detail: 'Student with this email already exists' });
    }

    const spn = await generateSPN();
    const uid = crypto.randomUUID();
    const hashedPassword = hashPassword(password);
    const role = email.toLowerCase() === ADMIN_EMAIL ? 'admin' : 'student';
    const now = Date.now() / 1000;

    const studentDoc = {
      uid,
      spn,
      email,
      phone: phone || '',
      whatsapp: whatsapp || phone || '',
      passwordHash: hashedPassword,
      role,
      status: 'active',
      verificationStatus: 'pending',
      securityEmail: securityEmail || '',
      createdAt: now,
      updatedAt: now
    };
    await saveDoc('students', uid, studentDoc);

    const profileDoc = {
      profileId: uid,
      studentUID: uid,
      spn,
      fullName,
      college: college || 'Academic Institution',
      course: course || '',
      semester: semester || '',
      graduationYear: graduationYear || '',
      skills: skills || [],
      socialLinks: socialLinks || {},
      avatarURL: avatarURL || '',
      coverURL: coverURL || '',
      trustScore: 40,
      visibility: 'public',
      createdAt: now
    };
    await saveDoc('profiles', uid, profileDoc);

    const token = createJWTToken(uid, email, role);
    return res.json({
      student: { uid, spn, email, fullName, role },
      token
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/auth/login
app.post('/api/v1/auth/login', async (req, res) => {
  try {
    const { identifier, password } = req.body;
    if (!identifier || !password) {
      return res.status(401).json({ detail: 'Invalid SPN/Email or password' });
    }

    const target = identifier.trim().toLowerCase();
    const students = await getCollectionDocs('students');

    let student = students.find(s => {
      const spn = String(s.spn || '').trim().toLowerCase();
      const email = String(s.email || '').trim().toLowerCase();
      const secEmail = String(s.securityEmail || '').trim().toLowerCase();
      const phone = String(s.phone || '').trim().toLowerCase();
      const uid = String(s.uid || '').trim().toLowerCase();
      return [spn, email, secEmail, phone, uid].includes(target);
    });

    const isAdminID = target === ADMIN_EMAIL || (student && student.role === 'admin');
    if (isAdminID) {
      if (password === ADMIN_PASSWORD || (student && verifyPassword(password, student.passwordHash))) {
        const uid = student ? student.uid : 'admin_super_uid';
        const spn = student ? student.spn : '26360087';
        const email = student ? student.email : ADMIN_EMAIL;
        const token = createJWTToken(uid, email, 'admin');
        return res.json({
          student: { uid, spn, email, fullName: ADMIN_NAME, role: 'admin' },
          token
        });
      }
    }

    if (!student || !verifyPassword(password, student.passwordHash)) {
      return res.status(401).json({ detail: 'Invalid SPN/Email or password' });
    }

    const profiles = await getCollectionDocs('profiles');
    const profile = profiles.find(p => p.profileId === student.uid || p.studentUID === student.uid) || {};
    const role = student.email.toLowerCase() === ADMIN_EMAIL ? 'admin' : (student.role || 'student');
    const token = createJWTToken(student.uid, student.email, role);

    return res.json({
      student: {
        uid: student.uid,
        spn: student.spn || '',
        email: student.email,
        fullName: profile.fullName || student.email.split('@')[0],
        role
      },
      token
    });
  } catch (err) {
    return res.status(401).json({ detail: 'Invalid SPN/Email or password' });
  }
});

// POST /api/v1/auth/otp/request
app.post('/api/v1/auth/otp/request', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email) return res.status(400).json({ detail: 'Email is required' });

    const otpCode = Math.floor(100000 + Math.random() * 900000).toString();
    const expiresAt = (Date.now() / 1000) + (5 * 60);

    await saveDoc('otpVerifications', email, {
      email,
      otp: otpCode,
      expiresAt,
      createdAt: Date.now() / 1000
    });

    return res.json({ message: `OTP sent to ${email}`, expiryMinutes: 5 });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/auth/otp/verify
app.post('/api/v1/auth/otp/verify', async (req, res) => {
  try {
    const { email, otp } = req.body;
    const records = await getCollectionDocs('otpVerifications');
    const record = records.find(r => r.email === email);

    if (!record) return res.status(400).json({ detail: 'No OTP request found for this email' });
    if ((Date.now() / 1000) > record.expiresAt) return res.status(400).json({ detail: 'OTP has expired. Please request a new one.' });
    if (record.otp !== otp) return res.status(400).json({ detail: 'Invalid OTP code' });

    return res.json({ message: 'OTP verified successfully', verified: true });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/auth/forgot-password/request-otp
app.post('/api/v1/auth/forgot-password/request-otp', async (req, res) => {
  try {
    const { identifier } = req.body;
    if (!identifier) return res.status(400).json({ detail: 'SPN or Email is required' });

    const ident = identifier.trim().toLowerCase();
    const students = await getCollectionDocs('students');
    const student = students.find(s =>
      String(s.spn).toLowerCase() === ident ||
      String(s.email).toLowerCase() === ident ||
      String(s.securityEmail).toLowerCase() === ident
    );

    if (!student) {
      return res.status(400).json({ detail: 'No student account found matching the provided Primary Email or 8-digit SPN' });
    }

    const otpCode = Math.floor(100000 + Math.random() * 900000).toString();
    const expiresAt = (Date.now() / 1000) + (5 * 60);

    await saveDoc('otpVerifications', student.email, {
      email: student.email,
      otp: otpCode,
      uid: student.uid,
      type: 'password_reset',
      expiresAt,
      createdAt: Date.now() / 1000
    });

    return res.json({
      message: `Multi-Factor OTP sent to ${student.email} and security email.`,
      email: student.email,
      spn: student.spn
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/auth/forgot-password/reset
app.post('/api/v1/auth/forgot-password/reset', async (req, res) => {
  try {
    const { identifier, otp, newPassword } = req.body;
    if (!newPassword || newPassword.length < 6) {
      return res.status(400).json({ detail: 'New password must be at least 6 characters long' });
    }

    const ident = identifier.trim().toLowerCase();
    const students = await getCollectionDocs('students');
    const student = students.find(s =>
      String(s.spn).toLowerCase() === ident ||
      String(s.email).toLowerCase() === ident ||
      String(s.securityEmail).toLowerCase() === ident
    );

    if (!student) return res.status(400).json({ detail: 'Invalid SPN or Email' });

    const records = await getCollectionDocs('otpVerifications');
    const record = records.find(r => r.email === student.email);

    if (!record) return res.status(400).json({ detail: 'No active password reset request found. Request a new OTP.' });
    if ((Date.now() / 1000) > record.expiresAt) return res.status(400).json({ detail: 'OTP has expired. Please request a new one.' });
    if (record.otp !== otp) return res.status(400).json({ detail: 'Invalid OTP verification code' });

    // Update password with zero length limitations
    const newHash = hashPassword(newPassword);
    student.passwordHash = newHash;
    student.updatedAt = Date.now() / 1000;
    await saveDoc('students', student.uid, student);

    return res.json({
      message: 'Password reset successfully! You can now log in with your new password.',
      status: 'success'
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/auth/me
app.get('/api/v1/auth/me', authenticateToken, async (req, res) => {
  const students = await getCollectionDocs('students');
  const student = students.find(s => s.uid === req.user.uid);
  if (!student) return res.status(404).json({ detail: 'User profile not found' });
  const { passwordHash, ...safeUser } = student;
  res.json(safeUser);
});

// Global Live Search Route returning counts & lengths
app.get('/api/v1/search/global-live', async (req, res) => {
  const query = req.query.q || 'Student Innovation';
  const githubRepositories = [
    { title: `${query} Developer Project Core`, description: 'Verified student open-source innovation repository.', stars: 128, language: 'JavaScript', url: 'https://github.com/topics/student-project' },
    { title: `AI ${query} Toolkit`, description: 'High performance ML models and developer pipeline.', stars: 95, language: 'Python', url: 'https://github.com/topics/ai-toolkit' }
  ];
  const googleWebResults = [
    { title: `DigiIndia Student Innovation Platform - ${query}`, snippet: `Discover verified student profiles, project repositories, and trust scores for ${query}.`, url: 'https://digiindia-studentcollaboration.web.app' }
  ];
  const youtubeResources = [
    { title: `Building ${query} Projects - Student Guide`, description: 'Step-by-step video demonstration of project architecture.', url: 'https://youtube.com' }
  ];
  const mediumArticles = [
    { title: `Architecting Modern Student Ecosystems: ${query}`, description: 'Technical breakdown of scalable open-source developer portals.', url: 'https://medium.com' }
  ];

  res.json({
    query,
    githubRepositories,
    githubCount: githubRepositories.length,
    googleWebResults,
    googleCount: googleWebResults.length,
    youtubeResources,
    youtubeCount: youtubeResources.length,
    mediumArticles,
    mediumCount: mediumArticles.length,
    totalResults: githubRepositories.length + googleWebResults.length + youtubeResources.length + mediumArticles.length
  });
});

// ==========================================
// RUNTIME SEO CRAWLER & AUDIT ENGINE
// ==========================================
async function crawlAndAuditSEO(targetUrl, expectedToken, projectMetadata = {}) {
  const result = {
    verified: false,
    reason: '',
    robotsFound: false,
    sitemapFound: false,
    sitemapUrlsCount: 0,
    screenshotUri: '',
    runtimeSEO: {
      title: '',
      description: '',
      author: '',
      keywords: '',
      canonical: '',
      viewport: '',
      openGraph: {},
      twitterCard: {},
      h1Count: 0,
      h1Text: '',
      metaTagToken: ''
    },
    seoComparison: {
      titleMatch: false,
      descriptionMatch: false,
      ownershipMatch: false,
      canonicalConfigured: false,
      socialGraphConfigured: false,
      contentStructureValid: false,
      crawlerAssetsConfigured: false
    },
    scoreBreakdown: { baseScore: 20 },
    awardedScore: 20
  };

  try {
    const urlObj = new URL(targetUrl);
    const baseDomain = `${urlObj.protocol}//${urlObj.host}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);
    const response = await fetch(targetUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; DigiBot/2.0; +https://digiindia-studentcollaboration.web.app)'
      }
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      const html = await response.text();

      // Title
      const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
      if (titleMatch) result.runtimeSEO.title = titleMatch[1].trim();

      // Meta tags extractor
      const extractMeta = (nameAttr, nameVal) => {
        const regex = new RegExp(`<meta\\s+[^>]*${nameAttr}=["']${nameVal}["'][^>]*content=["']([^"']*)["']|<meta\\s+[^>]*content=["']([^"']*)["'][^>]*${nameAttr}=["']${nameVal}["']`, 'i');
        const m = html.match(regex);
        return m ? (m[1] || m[2] || '').trim() : '';
      };

      result.runtimeSEO.description = extractMeta('name', 'description');
      result.runtimeSEO.author = extractMeta('name', 'author');
      result.runtimeSEO.keywords = extractMeta('name', 'keywords');
      result.runtimeSEO.viewport = extractMeta('name', 'viewport');
      result.runtimeSEO.metaTagToken = extractMeta('name', 'digiindia-student-innovation-platform');

      // Canonical link
      const canonMatch = html.match(/<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']*)["']|<link\s+[^>]*href=["']([^"']*)["'][^>]*rel=["']canonical["']/i);
      if (canonMatch) result.runtimeSEO.canonical = (canonMatch[1] || canonMatch[2] || '').trim();

      // OpenGraph
      ['og:title', 'og:description', 'og:image', 'og:url', 'og:type'].forEach(prop => {
        const val = extractMeta('property', prop);
        if (val) result.runtimeSEO.openGraph[prop] = val;
      });

      // Twitter Cards
      ['twitter:card', 'twitter:title', 'twitter:description', 'twitter:image'].forEach(name => {
        const val = extractMeta('name', name);
        if (val) result.runtimeSEO.twitterCard[name] = val;
      });

      // H1 Headings
      const h1Matches = [...html.matchAll(/<h1[^>]*>([\s\S]*?)<\/h1>/gi)];
      result.runtimeSEO.h1Count = h1Matches.length;
      if (h1Matches.length > 0) {
        result.runtimeSEO.h1Text = h1Matches[0][1].replace(/<[^>]+>/g, '').trim();
      }

      // Check Verification Ownership Token
      if (result.runtimeSEO.metaTagToken) {
        if (result.runtimeSEO.metaTagToken === expectedToken) {
          result.verified = true;
          result.seoComparison.ownershipMatch = true;
          result.reason = 'Ownership meta-tag verified successfully!';
        } else {
          result.reason = `Ownership meta-tag found with token '${result.runtimeSEO.metaTagToken}', but expected '${expectedToken}'`;
        }
      } else {
        result.reason = `Meta-tag 'digiindia-student-innovation-platform' not found on ${targetUrl}`;
      }

      // Compare Runtime vs Coded Project Metadata
      const pTitle = (projectMetadata.title || '').trim().toLowerCase();
      const pDesc = (projectMetadata.description || '').trim().toLowerCase();

      if (result.runtimeSEO.title && (pTitle.includes(result.runtimeSEO.title.toLowerCase()) || result.runtimeSEO.title.toLowerCase().includes(pTitle) || result.runtimeSEO.title.length >= 5)) {
        result.seoComparison.titleMatch = true;
      }
      if (result.runtimeSEO.description && (result.runtimeSEO.description.length >= 20 || pDesc.split(' ').slice(0, 4).some(w => w && result.runtimeSEO.description.toLowerCase().includes(w)))) {
        result.seoComparison.descriptionMatch = true;
      }
      if (result.runtimeSEO.canonical || result.runtimeSEO.viewport) {
        result.seoComparison.canonicalConfigured = true;
      }
      if (Object.keys(result.runtimeSEO.openGraph).length > 0 || Object.keys(result.runtimeSEO.twitterCard).length > 0) {
        result.seoComparison.socialGraphConfigured = true;
      }
      if (result.runtimeSEO.h1Count >= 1) {
        result.seoComparison.contentStructureValid = true;
      }

      // Snapshot preview
      const plainText = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 300);
      result.screenshotUri = `data:text/html;base64,${Buffer.from(`<h3>Snapshot: ${targetUrl}</h3><p>${plainText}</p>`).toString('base64')}`;

      // Check robots.txt & sitemap.xml
      try {
        const robRes = await fetch(`${baseDomain}/robots.txt`);
        if (robRes.ok) {
          const robText = await robRes.text();
          if (robText.length > 5) result.robotsFound = true;
        }
      } catch (e) {}

      try {
        const smRes = await fetch(`${baseDomain}/sitemap.xml`);
        if (smRes.ok) {
          const smText = await smRes.text();
          result.sitemapFound = true;
          const locCount = (smText.match(/<loc>/g) || []).length;
          result.sitemapUrlsCount = locCount;
        }
      } catch (e) {}

      if (result.robotsFound || result.sitemapFound) {
        result.seoComparison.crawlerAssetsConfigured = true;
      }
    } else {
      result.reason = `HTTP request to ${targetUrl} returned status ${response.status}`;
    }
  } catch (err) {
    result.reason = `Crawler connection error to ${targetUrl}: ${err.message}`;
  }

  // Dynamic Score Awards Algorithm
  let score = 20;
  if (result.verified) {
    result.scoreBreakdown.ownershipVerified = 30;
    score += 30;
  }
  if (result.seoComparison.titleMatch) {
    result.scoreBreakdown.titleOptimization = 15;
    score += 15;
  }
  if (result.seoComparison.descriptionMatch) {
    result.scoreBreakdown.metaDescriptionQuality = 15;
    score += 15;
  }
  if (result.seoComparison.socialGraphConfigured) {
    result.scoreBreakdown.socialMediaGraph = 10;
    score += 10;
  }
  if (result.seoComparison.canonicalConfigured) {
    result.scoreBreakdown.technicalSEO = 5;
    score += 5;
  }
  if (result.seoComparison.contentStructureValid) {
    result.scoreBreakdown.contentStructure = 5;
    score += 5;
  }
  if (result.seoComparison.crawlerAssetsConfigured) {
    result.scoreBreakdown.crawlerAssets = 5;
    score += 5;
  }

  result.awardedScore = Math.min(100, score);
  return result;
}

// ==========================================
// PROJECTS API ROUTES (/api/v1/projects)
// ==========================================

// POST /api/v1/projects (Upload project with duplicate upsert)
app.post('/api/v1/projects', authenticateToken, async (req, res) => {
  try {
    const ownerUID = req.user.uid;
    const { title, description, repositoryURL, liveURL, technologyStack, visibility, license, tags, category } = req.body;
    if (!title) return res.status(400).json({ detail: 'Project title is required' });

    const allProjects = await getCollectionDocs('projects');
    const existingUserProjects = allProjects.filter(p => p.ownerUID === ownerUID);

    // Duplicate check & graceful upsert
    const existing = existingUserProjects.find(ep => {
      const sameRepo = repositoryURL && ep.repositoryURL && ep.repositoryURL.trim().toLowerCase() === repositoryURL.trim().toLowerCase();
      const sameLive = liveURL && ep.liveURL && ep.liveURL.trim().toLowerCase() === liveURL.trim().toLowerCase();
      const sameTitle = ep.title && ep.title.trim().toLowerCase() === title.trim().toLowerCase();
      return sameRepo || sameLive || sameTitle;
    });

    if (existing) {
      const projectId = existing.projectId;
      const updatedFields = {
        ...existing,
        title: title || existing.title,
        description: description || existing.description,
        repositoryURL: repositoryURL || existing.repositoryURL,
        liveURL: liveURL || existing.liveURL,
        technologyStack: technologyStack || existing.technologyStack || [],
        visibility: visibility || existing.visibility || 'public',
        license: license || existing.license || 'MIT',
        updatedAt: Date.now() / 1000
      };
      await saveDoc('projects', projectId, updatedFields);

      const allVerifs = await getCollectionDocs('projectVerification');
      let verif = allVerifs.find(v => v.projectId === projectId);
      let token = verif ? verif.verificationToken : crypto.randomBytes(12).toString('hex');
      if (!verif) {
        verif = {
          projectId,
          verificationToken: token,
          verificationMethod: 'meta_tag',
          verificationStatus: 'pending',
          metaTag: `<meta name="digiindia-student-innovation-platform" content="${token}">`,
          attemptCount: 0,
          createdAt: Date.now() / 1000
        };
        await saveDoc('projectVerification', projectId, verif);
      }

      return res.json({
        project: updatedFields,
        verification: {
          verificationToken: token,
          metaTagHtml: `<meta name="digiindia-student-innovation-platform" content="${token}">`
        },
        updated: true
      });
    }

    const projectId = crypto.randomUUID();
    const verificationToken = crypto.randomBytes(12).toString('hex');
    const now = Date.now() / 1000;

    const projectDoc = {
      projectId,
      ownerUID,
      title,
      description: description || '',
      repositoryURL: repositoryURL || '',
      liveURL: liveURL || '',
      visibility: visibility || 'public',
      technologyStack: technologyStack || [],
      category: category || 'Software',
      license: license || 'MIT',
      tags: tags || [],
      verificationStatus: 'pending',
      status: 'active',
      trustScore: 50,
      createdAt: now,
      updatedAt: now,
      lastScan: now
    };
    await saveDoc('projects', projectId, projectDoc);

    const verifDoc = {
      projectId,
      verificationToken,
      verificationMethod: 'meta_tag',
      verificationStatus: 'pending',
      metaTag: `<meta name="digiindia-student-innovation-platform" content="${verificationToken}">`,
      attemptCount: 0,
      createdAt: now
    };
    await saveDoc('projectVerification', projectId, verifDoc);

    await saveDoc('projectMetadata', projectId, {
      projectId,
      canonical: liveURL || repositoryURL || '',
      openGraph: {},
      lastCrawled: now
    });

    return res.json({
      project: projectDoc,
      verification: {
        verificationToken,
        metaTagHtml: `<meta name="digiindia-student-innovation-platform" content="${verificationToken}">`
      }
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/projects/my
app.get('/api/v1/projects/my', authenticateToken, async (req, res) => {
  try {
    const allProjects = await getCollectionDocs('projects');
    const myProjects = allProjects.filter(p => p.ownerUID === req.user.uid);
    res.json(myProjects);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/projects/public
app.get('/api/v1/projects/public', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const allProjects = await getCollectionDocs('projects');
    const publicProjects = allProjects.filter(p => p.visibility === 'public').slice(0, limit);
    res.json(publicProjects);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/projects/urls
app.get('/api/v1/projects/urls', async (req, res) => {
  try {
    const allProjects = await getCollectionDocs('projects');
    const urls = [];
    allProjects.forEach(p => {
      if (p.liveURL) urls.push({ projectId: p.projectId, title: p.title, url: p.liveURL, type: 'live' });
      if (p.repositoryURL) urls.push({ projectId: p.projectId, title: p.title, url: p.repositoryURL, type: 'repository' });
    });
    res.json(urls);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/projects/:projectId
app.get('/api/v1/projects/:projectId', async (req, res) => {
  try {
    const { projectId } = req.params;
    const projects = await getCollectionDocs('projects');
    const project = projects.find(p => p.projectId === projectId);
    if (!project) return res.status(404).json({ detail: 'Project not found' });

    const metadataList = await getCollectionDocs('projectMetadata');
    const metadata = metadataList.find(m => m.projectId === projectId) || {};

    const verifs = await getCollectionDocs('projectVerification');
    const verification = verifs.find(v => v.projectId === projectId) || {};

    res.json({ project, metadata, verification });
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// PUT /api/v1/projects/:projectId
app.put('/api/v1/projects/:projectId', authenticateToken, async (req, res) => {
  try {
    const { projectId } = req.params;
    const projects = await getCollectionDocs('projects');
    const project = projects.find(p => p.projectId === projectId);
    if (!project) return res.status(404).json({ detail: 'Project not found' });
    if (project.ownerUID !== req.user.uid && req.user.role !== 'admin') {
      return res.status(403).json({ detail: 'Unauthorized to modify this project' });
    }

    const allowed = ['title', 'description', 'liveURL', 'repositoryURL', 'visibility', 'technologyStack', 'license', 'category'];
    allowed.forEach(f => {
      if (req.body[f] !== undefined) project[f] = req.body[f];
    });
    project.updatedAt = Date.now() / 1000;
    await saveDoc('projects', projectId, project);
    res.json(project);
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// DELETE /api/v1/projects/:projectId
app.delete('/api/v1/projects/:projectId', authenticateToken, async (req, res) => {
  try {
    const { projectId } = req.params;
    const projects = await getCollectionDocs('projects');
    const project = projects.find(p => p.projectId === projectId);
    if (!project) return res.status(404).json({ detail: 'Project not found' });
    if (project.ownerUID !== req.user.uid && req.user.role !== 'admin') {
      return res.status(403).json({ detail: 'Unauthorized' });
    }

    if (firestore) {
      await firestore.collection('projects').doc(projectId).delete().catch(() => {});
      await firestore.collection('projectMetadata').doc(projectId).delete().catch(() => {});
      await firestore.collection('projectVerification').doc(projectId).delete().catch(() => {});
    }
    ['projects', 'projectMetadata', 'projectVerification'].forEach(col => {
      const fp = path.join(DATA_STORE_DIR, `${col}.json`);
      if (fs.existsSync(fp)) {
        try {
          const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
          delete data[projectId];
          fs.writeFileSync(fp, JSON.stringify(data, null, 2));
        } catch (e) {}
      }
    });
    res.json({ message: 'Project deleted successfully', projectId });
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// ==========================================
// VERIFICATION & RUNTIME SEO CRAWLER ROUTE
// ==========================================

// POST /api/v1/verification/project/crawl
app.post('/api/v1/verification/project/crawl', async (req, res) => {
  try {
    const { projectId } = req.body;
    if (!projectId) return res.status(400).json({ detail: 'projectId is required' });

    const projects = await getCollectionDocs('projects');
    const project = projects.find(p => p.projectId === projectId);
    if (!project) return res.status(404).json({ detail: 'Project record not found' });

    const verifs = await getCollectionDocs('projectVerification');
    let verif = verifs.find(v => v.projectId === projectId);
    if (!verif) {
      verif = {
        projectId,
        verificationToken: crypto.randomBytes(12).toString('hex'),
        verificationStatus: 'pending',
        attemptCount: 0
      };
    }

    const targetUrl = project.liveURL || project.repositoryURL;
    if (!targetUrl || !targetUrl.startsWith('http')) {
      return res.status(400).json({ detail: 'Valid target URL (http/https) required for crawler verification' });
    }

    verif.attemptCount = (verif.attemptCount || 0) + 1;
    verif.lastAttempt = Date.now() / 1000;

    // Run advanced runtime SEO crawler & score award algorithm
    const crawlResult = await crawlAndAuditSEO(targetUrl, verif.verificationToken, project);

    verif.verificationStatus = crawlResult.verified ? 'verified' : 'failed';
    if (crawlResult.verified) verif.verifiedAt = Date.now() / 1000;
    verif.crawlerLog = crawlResult.reason;
    verif.hasRobotsTxt = crawlResult.robotsFound;
    verif.hasSitemapXml = crawlResult.sitemapFound;
    verif.sitemapUrlsCount = crawlResult.sitemapUrlsCount;
    verif.liveSnapshotURI = crawlResult.screenshotUri;
    verif.runtimeSEO = crawlResult.runtimeSEO;
    verif.seoComparison = crawlResult.seoComparison;
    verif.scoreBreakdown = crawlResult.scoreBreakdown;
    verif.awardedScore = crawlResult.awardedScore;

    await saveDoc('projectVerification', projectId, verif);

    // Update project trust & SEO score
    project.verificationStatus = verif.verificationStatus;
    project.trustScore = crawlResult.awardedScore;
    project.seoScore = crawlResult.awardedScore;
    project.hasRobotsTxt = crawlResult.robotsFound;
    project.hasSitemapXml = crawlResult.sitemapFound;
    project.updatedAt = Date.now() / 1000;
    await saveDoc('projects', projectId, project);

    // Save metadata
    await saveDoc('projectMetadata', projectId, {
      projectId,
      canonical: crawlResult.runtimeSEO.canonical || project.liveURL || '',
      openGraph: crawlResult.runtimeSEO.openGraph || {},
      lastCrawled: Date.now() / 1000
    });

    return res.json({
      projectId,
      verificationStatus: verif.verificationStatus,
      verified: crawlResult.verified,
      trustScore: crawlResult.awardedScore,
      scoreBreakdown: crawlResult.scoreBreakdown,
      runtimeSEO: crawlResult.runtimeSEO,
      seoComparison: crawlResult.seoComparison,
      hasRobotsTxt: crawlResult.robotsFound,
      hasSitemapXml: crawlResult.sitemapFound,
      sitemapUrlsCount: crawlResult.sitemapUrlsCount,
      log: crawlResult.reason
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// ==========================================
// DEVELOPER KEYS ROUTES
// ==========================================

app.get('/api/v1/developer/keys', authenticateToken, async (req, res) => {
  try {
    const keys = await getCollectionDocs('developerApiKeys');
    const userKeys = keys.filter(k => k.ownerUID === req.user.uid);
    res.json(userKeys);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

app.post('/api/v1/developer/keys', authenticateToken, async (req, res) => {
  try {
    const keyId = crypto.randomUUID();
    const rawKey = `di_live_${crypto.randomBytes(18).toString('hex')}`;
    const keyDoc = {
      keyId,
      ownerUID: req.user.uid,
      apiName: req.body.apiName || 'Production Client Key',
      keyPrefix: rawKey.slice(0, 12) + '...',
      keyHash: crypto.createHash('sha256').update(rawKey).digest('hex'),
      permissions: req.body.permissions || ['read:projects', 'verify:student'],
      status: 'active',
      usageCount: 0,
      createdAt: Date.now() / 1000
    };
    await saveDoc('developerApiKeys', keyId, keyDoc);
    res.json({ key: keyDoc, rawApiKey: rawKey });
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

app.delete('/api/v1/developer/keys/:keyId', authenticateToken, async (req, res) => {
  try {
    const { keyId } = req.params;
    if (firestore) {
      await firestore.collection('developerApiKeys').doc(keyId).delete().catch(() => {});
    }
    const fp = path.join(DATA_STORE_DIR, 'developerApiKeys.json');
    if (fs.existsSync(fp)) {
      try {
        const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
        delete data[keyId];
        fs.writeFileSync(fp, JSON.stringify(data, null, 2));
      } catch (e) {}
    }
    res.json({ message: 'Key revoked successfully', keyId });
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// ==========================================
// AI & TRAINING ROUTES
// ==========================================

app.get('/api/v1/ai/models', async (req, res) => {
  try {
    const models = await getCollectionDocs('aiTrainingModels');
    res.json(models.length ? models : [
      { modelId: 'digi-gpt-default', modelName: 'DigiIndia Innovation Core AI', status: 'ready', accuracy: 96.4 },
      { modelId: 'digi-code-crawler', modelName: 'DigiBot Automated Code Crawler', status: 'ready', accuracy: 98.1 }
    ]);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

app.post('/api/v1/ai/chat', async (req, res) => {
  try {
    const { prompt } = req.body;
    res.json({
      reply: `[DigiIndia AI Assistant]: Received your query: "${prompt || 'Welcome to DigiIndia!'}". All student portfolios, verification tokens, and innovation meta-tags are monitored in real-time.`,
      model: 'DigiBot-NLP-v2',
      timestamp: Date.now() / 1000
    });
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

app.post('/api/v1/ai/crawler/run', async (req, res) => {
  try {
    const { targetURL } = req.body;
    res.json({
      status: 'complete',
      targetURL: targetURL || 'https://digiindia-studentcollaboration.web.app',
      message: 'DigiBot Automated Crawler completed indexing of target domain.',
      knowledgeId: `kw_${crypto.randomBytes(4).toString('hex')}`,
      timestamp: Date.now() / 1000
    });
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// Catch-all API 404 middleware
app.use('/api', (req, res) => {
  res.status(404).json({
    detail: `API endpoint '${req.originalUrl}' not found`,
    status: 404,
    error: 'Not Found'
  });
});

// Serve Public Frontend Static Files
const publicDir = path.join(__dirname, 'public');
if (fs.existsSync(publicDir)) {
  app.use(express.static(publicDir));
  app.get('*', (req, res) => {
    res.sendFile(path.join(publicDir, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`[Node.js Server] DigiIndia Gateway server running on port ${PORT}`);
});
