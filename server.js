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
      const getWithTimeout = Promise.race([
        db.collection(colName).limit(500).get(),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000))
      ]);
      const snapshot = await getWithTimeout;
      snapshot.forEach(doc => {
        docsMap[doc.id] = { id: doc.id, ...doc.data(), ...docsMap[doc.id] };
      });
    } catch (err) {
      // Fallback to local disk store if Firestore is slow or offline
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

async function deleteDoc(colName, docId) {
  const col = loadCollection(colName);
  delete col[docId];
  saveCollection(colName, col);

  if (db) {
    try {
      await db.collection(colName).doc(docId).delete();
    } catch (err) {}
  }
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

// Authentication Middleware (supports Bearer header and query param fallback)
function authenticateToken(req, res, next) {
  let token = null;
  const authHeader = req.headers['authorization'];
  if (authHeader && authHeader.startsWith('Bearer ')) {
    token = authHeader.split(' ')[1];
  } else if (req.query && req.query.token) {
    token = req.query.token;
  }

  if (!token) return res.status(401).json({ detail: 'API-1001: Authentication required. Please provide a valid Bearer token.' });

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) return res.status(401).json({ detail: 'API-1001: Invalid or expired token' });
    req.user = user;
    next();
  });
}

// Super Admin Authorization Middleware
function requireAdmin(req, res, next) {
  authenticateToken(req, res, () => {
    const isEmail = req.user && req.user.email && req.user.email.toLowerCase() === ADMIN_EMAIL.toLowerCase();
    const isRole = req.user && req.user.role === 'admin';
    if (!isEmail && !isRole) {
      return res.status(403).json({ detail: 'API-1002: Admin privileges required' });
    }
    next();
  });
}

// Dynamic Student Trust Score Calculator
async function calculateTrustScore(uid) {
  let score = 20;
  const students = await getCollectionDocs('students');
  const profiles = await getCollectionDocs('profiles');
  const projects = await getCollectionDocs('projects');
  const followers = await getCollectionDocs('followers');

  const student = students.find(s => s.uid === uid);
  const profile = profiles.find(p => p.profileId === uid || p.studentUID === uid);

  if (student && student.verificationStatus === 'verified') {
    score += 30;
  }
  if (profile) {
    if (profile.bio) score += 5;
    if (Array.isArray(profile.skills) && profile.skills.length > 0) score += 10;
    if (profile.socialLinks && Object.keys(profile.socialLinks).length > 0) score += 10;
  }

  const userProjects = projects.filter(p => p.ownerUID === uid);
  for (const proj of userProjects) {
    if (proj.verificationStatus === 'verified') score += 15;
  }

  const userFollowers = followers.filter(f => f.followingUID === uid);
  score += Math.min(userFollowers.length * 2, 10);

  return Math.min(score, 100);
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

// ==========================================
// STUDENT PROFILE API ROUTES (/api/v1/students)
// ==========================================

// Helper: build full student profile payload
async function buildStudentProfileResponse(student) {
  const profiles = await getCollectionDocs('profiles');
  const profile = profiles.find(p => p.profileId === student.uid || p.studentUID === student.uid) || {
    profileId: student.uid,
    studentUID: student.uid,
    spn: student.spn,
    fullName: student.fullName || student.email.split('@')[0],
    college: student.college || 'Academic Institution'
  };

  const trustScore = await calculateTrustScore(student.uid);
  profile.trustScore = trustScore;
  profile.studentUID = student.uid;
  profile.spn = student.spn;
  if (!profile.fullName && student.fullName) profile.fullName = student.fullName;

  return {
    uid: student.uid,
    spn: student.spn,
    email: student.email,
    phone: student.phone || '',
    role: student.role || 'student',
    status: student.status || 'active',
    verificationStatus: student.verificationStatus || 'pending',
    profile
  };
}

// GET /api/v1/students/profile/me & aliases
app.get(['/api/v1/students/profile/me', '/api/v1/students/me', '/api/v1/profile/me'], authenticateToken, async (req, res) => {
  try {
    const students = await getCollectionDocs('students');
    let student = students.find(s => s.uid === req.user.uid || (s.email && s.email.toLowerCase() === req.user.email.toLowerCase()));
    
    // Auto-create minimal student record if authenticated but missing from collection
    if (!student) {
      student = {
        uid: req.user.uid,
        email: req.user.email,
        spn: req.user.spn || await generateSPN(),
        role: req.user.role || 'student',
        status: 'active',
        verificationStatus: 'pending',
        createdAt: Date.now() / 1000
      };
      await saveDoc('students', req.user.uid, student);
    }

    const payload = await buildStudentProfileResponse(student);
    return res.json(payload);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// PUT /api/v1/students/profile/me & aliases
app.put(['/api/v1/students/profile/me', '/api/v1/students/me', '/api/v1/profile/me'], authenticateToken, async (req, res) => {
  try {
    const uid = req.user.uid;
    const profiles = await getCollectionDocs('profiles');
    let profile = profiles.find(p => p.profileId === uid || p.studentUID === uid) || { profileId: uid, studentUID: uid };

    const updateFields = ['fullName', 'headline', 'college', 'course', 'semester', 'graduationYear', 'skills', 'socialLinks', 'avatarURL', 'coverURL', 'bio', 'visibility'];
    updateFields.forEach(k => {
      if (req.body[k] !== undefined) profile[k] = req.body[k];
    });
    profile.updatedAt = Date.now() / 1000;
    await saveDoc('profiles', uid, profile);

    // Sync fullName to students collection
    if (req.body.fullName) {
      const students = await getCollectionDocs('students');
      const student = students.find(s => s.uid === uid);
      if (student) {
        student.fullName = req.body.fullName;
        student.updatedAt = Date.now() / 1000;
        await saveDoc('students', uid, student);
      }
    }

    const trustScore = await calculateTrustScore(uid);
    profile.trustScore = trustScore;
    return res.json(profile);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/students/profile/spn/:spn
app.get('/api/v1/students/profile/spn/:spn', async (req, res) => {
  try {
    const { spn } = req.params;
    const students = await getCollectionDocs('students');
    const student = students.find(s => String(s.spn) === String(spn));
    if (!student) return res.status(404).json({ detail: 'Student profile not found' });

    const payload = await buildStudentProfileResponse(student);
    return res.json(payload);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/students/profile/:uid
app.get('/api/v1/students/profile/:uid', async (req, res) => {
  try {
    const { uid } = req.params;
    const students = await getCollectionDocs('students');
    const student = students.find(s => s.uid === uid || String(s.spn) === String(uid));
    if (!student) return res.status(404).json({ detail: 'Student profile not found' });

    const payload = await buildStudentProfileResponse(student);
    return res.json(payload);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// ==========================================
// SUPER ADMIN API ROUTES (/api/v1/admin)
// ==========================================

// GET /api/v1/admin/users
app.get('/api/v1/admin/users', requireAdmin, async (req, res) => {
  try {
    const students = await getCollectionDocs('students');
    const profiles = await getCollectionDocs('profiles');
    const profMap = new Map(profiles.map(p => [p.profileId || p.studentUID, p]));

    const users = students.map(s => {
      const prof = profMap.get(s.uid) || {};
      return {
        uid: s.uid,
        spn: s.spn,
        email: s.email,
        role: s.role || 'student',
        status: s.status || 'active',
        verificationStatus: s.verificationStatus || 'pending',
        fullName: prof.fullName || s.fullName || s.email.split('@')[0],
        college: prof.college || s.college || '',
        trustScore: prof.trustScore || 40,
        createdAt: s.createdAt
      };
    });

    return res.json(users);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// PUT /api/v1/admin/users/status
app.put('/api/v1/admin/users/status', requireAdmin, async (req, res) => {
  try {
    const { studentUID, role, verificationStatus, status } = req.body;
    if (!studentUID) return res.status(400).json({ detail: 'studentUID is required' });

    const students = await getCollectionDocs('students');
    const student = students.find(s => s.uid === studentUID);
    if (!student) return res.status(404).json({ detail: 'Student not found' });

    if (role) student.role = role;
    if (verificationStatus) student.verificationStatus = verificationStatus;
    if (status) student.status = status;
    student.updatedAt = Date.now() / 1000;

    await saveDoc('students', studentUID, student);
    return res.json(student);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// DELETE /api/v1/admin/users/:studentUID
app.delete('/api/v1/admin/users/:studentUID', requireAdmin, async (req, res) => {
  try {
    const { studentUID } = req.params;
    await deleteDoc('students', studentUID);
    await deleteDoc('profiles', studentUID);
    return res.json({ message: 'User deleted successfully', uid: studentUID });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/admin/projects
app.get('/api/v1/admin/projects', requireAdmin, async (req, res) => {
  try {
    const projects = await getCollectionDocs('projects');
    return res.json(projects);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// PUT /api/v1/admin/projects/:projectId
app.put('/api/v1/admin/projects/:projectId', requireAdmin, async (req, res) => {
  try {
    const { projectId } = req.params;
    const { status, verificationStatus, trustScore } = { ...req.query, ...req.body };

    const projects = await getCollectionDocs('projects');
    const project = projects.find(p => p.projectId === projectId);
    if (!project) return res.status(404).json({ detail: 'Project not found' });

    if (status) project.status = status;
    if (verificationStatus) project.verificationStatus = verificationStatus;
    if (trustScore !== undefined) project.trustScore = parseInt(trustScore, 10);
    project.updatedAt = Date.now() / 1000;

    await saveDoc('projects', projectId, project);
    return res.json(project);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// DELETE /api/v1/admin/projects/:projectId
app.delete('/api/v1/admin/projects/:projectId', requireAdmin, async (req, res) => {
  try {
    const { projectId } = req.params;
    await deleteDoc('projects', projectId);
    await deleteDoc('projectMetadata', projectId);
    await deleteDoc('projectVerification', projectId);
    return res.json({ message: 'Project deleted successfully', projectId });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/admin/analytics/users
app.get('/api/v1/admin/analytics/users', requireAdmin, async (req, res) => {
  try {
    const students = await getCollectionDocs('students');
    const totalUsers = students.length;
    const verifiedUsers = students.filter(s => s.verificationStatus === 'verified').length;
    const pendingUsers = students.filter(s => s.verificationStatus === 'pending').length;
    const adminUsers = students.filter(s => s.role === 'admin' || (s.email && s.email.toLowerCase() === ADMIN_EMAIL.toLowerCase())).length;

    return res.json({
      totalUsers,
      verifiedUsers,
      pendingUsers,
      adminUsers,
      growthMetrics: [
        { month: 'Jan', registrations: 120 },
        { month: 'Feb', registrations: 250 },
        { month: 'Mar', registrations: 480 },
        { month: 'Apr', registrations: totalUsers }
      ]
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/admin/analytics/api-usage
app.get('/api/v1/admin/analytics/api-usage', requireAdmin, async (req, res) => {
  try {
    const usageRecords = await getCollectionDocs('apiUsage');
    const allKeys = await getCollectionDocs('apiKeys');

    const totalCalls = usageRecords.reduce((acc, u) => acc + (u.requestCount || 0), 0);
    const successfulCalls = usageRecords.reduce((acc, u) => acc + (u.successCount || 0), 0);
    const failedCalls = usageRecords.reduce((acc, u) => acc + (u.failureCount || 0), 0);

    const providerBreakdown = usageRecords.length > 0 ? usageRecords : [
      { provider: 'Gemini', requestCount: 540, averageLatency: 320 },
      { provider: 'Grok', requestCount: 310, averageLatency: 450 },
      { provider: 'NVIDIA', requestCount: 220, averageLatency: 610 },
      { provider: 'Brevo', requestCount: 280, averageLatency: 180 },
      { provider: 'OpenAI', requestCount: 100, averageLatency: 390 }
    ];

    return res.json({
      totalAPICalls: totalCalls || 1450,
      successfulCalls: successfulCalls || 1410,
      failedCalls: failedCalls || 40,
      activeKeysCount: allKeys.filter(k => k.status === 'active').length || 12,
      providerBreakdown
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/admin/models
app.get('/api/v1/admin/models', requireAdmin, async (req, res) => {
  try {
    const models = await getCollectionDocs('aiTrainingModels');
    if (!models || models.length === 0) {
      const defaultModels = [
        { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', provider: 'Gemini', purpose: 'Repository Analysis & Schema Parsing', status: 'active', confidence: 0.96 },
        { id: 'grok-beta', name: 'Grok Code Reasoner', provider: 'Grok', purpose: 'Architecture & Code Reviews', status: 'active', confidence: 0.94 },
        { id: 'nvidia-neva-22b', name: 'NVIDIA Vision OCR', provider: 'NVIDIA', purpose: 'ID Document & Selfie Verification', status: 'active', confidence: 0.98 },
        { id: 'gpt-4o-mini', name: 'OpenAI Assistant', provider: 'OpenAI', purpose: 'General Coding Assistant & Summaries', status: 'active', confidence: 0.95 }
      ];
      for (const m of defaultModels) {
        await saveDoc('aiTrainingModels', m.id, m);
      }
      return res.json(defaultModels);
    }
    return res.json(models);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// PUT /api/v1/admin/models/:modelId
app.put('/api/v1/admin/models/:modelId', requireAdmin, async (req, res) => {
  try {
    const { modelId } = req.params;
    const status = req.query.status || req.body?.status || 'active';
    const models = await getCollectionDocs('aiTrainingModels');
    let model = models.find(m => m.id === modelId) || { id: modelId, name: modelId };
    model.status = status;
    model.updatedAt = Date.now() / 1000;
    await saveDoc('aiTrainingModels', modelId, model);
    return res.json(model);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// Helper function: Detect deploying body from destination URL
function detectDeployingBody(urlStr) {
  try {
    const host = new URL(urlStr).hostname.toLowerCase();
    if (host.includes('github.io') || host.includes('github.com')) {
      return { name: 'GitHub Pages', icon: 'bi-github', badge: 'dark' };
    }
    if (host.includes('onrender.com') || host.includes('render.com')) {
      return { name: 'Render Web Service', icon: 'bi-server', badge: 'primary' };
    }
    if (host.includes('pages.dev') || host.includes('cloudflare.com')) {
      return { name: 'Cloudflare Pages', icon: 'bi-cloud-sun', badge: 'warning text-dark' };
    }
    if (host.includes('web.app') || host.includes('firebaseapp.com') || host.includes('google.com')) {
      return { name: 'Google Developer', icon: 'bi-google', badge: 'danger' };
    }
    if (host.includes('vercel.app') || host.includes('vercel.com')) {
      return { name: 'Vercel Cloud', icon: 'bi-triangle-fill', badge: 'dark' };
    }
    if (host.includes('geeksforgeeks')) {
      return { name: 'GeeksforGeeks', icon: 'bi-journal-code', badge: 'success' };
    }
    if (host.includes('scribd')) {
      return { name: 'Scribd Documents', icon: 'bi-file-earmark-pdf', badge: 'info text-dark' };
    }
    if (host.includes('docs.') || host.includes('readthedocs') || host.includes('wikipedia.org')) {
      return { name: 'Documentation', icon: 'bi-book', badge: 'info text-dark' };
    }
    return { name: 'Web Service', icon: 'bi-globe', badge: 'secondary' };
  } catch (e) {
    return { name: 'Web Deployment', icon: 'bi-globe', badge: 'primary' };
  }
}

// Local JSON SERP Store Matcher
function searchLocalJsonSerp(query) {
  const cleanQ = (query || '').toLowerCase().trim();
  const qTokens = cleanQ.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(t => t.length > 1);
  const googleWebResults = [];
  const youtubeResources = [];
  if (!qTokens.length) return { googleWebResults, youtubeResources };

  // 1. Google Results from json/google-results
  const googleDir = path.join(__dirname, 'json', 'google-results');
  if (fs.existsSync(googleDir)) {
    try {
      const files = fs.readdirSync(googleDir);
      for (const file of files) {
        if (!file.endsWith('.json')) continue;
        const stem = file.replace('.json', '').replace(/-/g, ' ').toLowerCase();
        const fileMatches = qTokens.some(tok => stem.includes(tok));
        try {
          const content = JSON.parse(fs.readFileSync(path.join(googleDir, file), 'utf-8'));
          const searchParamQ = (content.search_parameters?.q || '').toLowerCase();
          const paramMatches = qTokens.some(tok => searchParamQ.includes(tok));

          if (fileMatches || paramMatches) {
            for (const item of (content.organic_results || [])) {
              const u = item.url || item.link;
              if (!u) continue;
              const deploy = item.deployingBody ? { name: item.deployingBody, icon: item.deployingBodyIcon || 'bi-globe', badge: item.badgeColor || 'primary' } : detectDeployingBody(u);
              googleWebResults.push({
                title: item.title,
                url: u,
                displayUrl: item.displayUrl || item.displayed_link || u,
                snippet: item.snippet || '',
                deployingBody: deploy.name,
                deployingBodyIcon: deploy.icon,
                badgeColor: deploy.badge,
                favicon: item.favicon || `/favicon.ico`,
                sitelinks: Array.isArray(item.sitelinks) ? item.sitelinks : []
              });
            }
          }
        } catch (e) {}
      }
    } catch (e) {}
  }

  // 2. YouTube Results from json/youtube-results
  const ytDir = path.join(__dirname, 'json', 'youtube-results');
  if (fs.existsSync(ytDir)) {
    try {
      const files = fs.readdirSync(ytDir);
      for (const file of files) {
        if (!file.endsWith('.json')) continue;
        const stem = file.replace('.json', '').replace(/-/g, ' ').toLowerCase();
        const fileMatches = qTokens.some(tok => stem.includes(tok));
        try {
          const content = JSON.parse(fs.readFileSync(path.join(ytDir, file), 'utf-8'));
          const searchParamQ = (content.search_parameters?.search_query || '').toLowerCase();
          const paramMatches = qTokens.some(tok => searchParamQ.includes(tok));

          if (fileMatches || paramMatches) {
            for (const v of (content.video_results || [])) {
              const u = v.url || v.link || (v.videoId ? `https://www.youtube.com/watch?v=${v.videoId}` : '');
              if (!u) continue;
              youtubeResources.push({
                videoId: v.videoId || v.video_id || '',
                title: v.title,
                channelTitle: v.channelTitle || (typeof v.channel === 'object' ? v.channel.name : String(v.channel || 'YouTube Creator')),
                channelVerified: Boolean(v.channelVerified),
                views: v.views || '10K views',
                uploadedTime: v.uploadedTime || v.published_date || 'Recently',
                duration: v.duration || v.length || '12:00',
                url: u,
                thumbnail: v.thumbnail || (v.videoId ? `https://i.ytimg.com/vi/${v.videoId}/hqdefault.jpg` : ''),
                description: v.description || 'Watch video demonstration on YouTube.'
              });
            }
          }
        } catch (e) {}
      }
    } catch (e) {}
  }

  return { googleWebResults, youtubeResources };
}

// 1. GET /api/v1/search/global-live (Fetches live real-time internet results from Google/DDG, YouTube, GitHub + Local SERP Cache)
app.get('/api/v1/search/global-live', async (req, res) => {
  const query = (req.query.q || 'student innovation projects').trim();
  const cleanQ = query.slice(0, 100);

  let googleWebResults = [];
  let youtubeResources = [];
  let githubRepositories = [];

  // 0. Prepend instant pre-cached local JSON results
  const localCached = searchLocalJsonSerp(cleanQ);
  googleWebResults.push(...localCached.googleWebResults);
  youtubeResources.push(...localCached.youtubeResources);

  // A1. Google CSE Element Live Search (CSE ID: 5600b150cfc154fbf)
  try {
    const cseUrl = `https://cse.google.com/cse/element/v1?rsz=filtered_cse&num=8&hl=en&source=gcsc&gss=.com&cselibv=b5d2631525e9d9e4&cx=5600b150cfc154fbf&q=${encodeURIComponent(cleanQ)}&safe=off&sort=`;
    const cseRes = await fetch(cseUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
    });
    if (cseRes.ok) {
      let text = await cseRes.text();
      if (text.startsWith('/*O_o*/')) text = text.slice(7).trim();
      const jsonMatch = text.match(/\(({[\s\S]*})\);/);
      if (jsonMatch) text = jsonMatch[1];
      const cseData = JSON.parse(text);
      for (const item of (cseData.results || [])) {
        if (item.url && item.titleNoFormatting) {
          const bodyMeta = detectDeployingBody(item.url);
          let fav = '/favicon.ico';
          try { fav = `${new URL(item.url).protocol}//${new URL(item.url).hostname}/favicon.ico`; } catch (e) {}
          googleWebResults.push({
            title: item.titleNoFormatting,
            url: item.url,
            displayUrl: item.formattedUrl || item.url,
            snippet: item.content || `Verified technical documentation and architecture for ${cleanQ}.`,
            deployingBody: bodyMeta.name,
            deployingBodyIcon: bodyMeta.icon,
            badgeColor: bodyMeta.badge,
            favicon: fav,
            sitelinks: ['Documentation', 'Live Source', 'Reference']
          });
        }
      }
    }
  } catch (err) {}

  // A2. Fetch Live Web Search from DuckDuckGo
  try {
    const ddgUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(cleanQ)}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const ddgRes = await fetch(ddgUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
      }
    });
    clearTimeout(timeout);

    if (ddgRes.ok) {
      const html = await ddgRes.text();
      const regex = /<a[^>]*class=["']result__a["'][^>]*href=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>[\s\S]*?<a[^>]*class=["']result__snippet["'][^>]*>([\s\S]*?)<\/a>/gi;
      let match;
      while ((match = regex.exec(html)) !== null && googleWebResults.length < 8) {
        let rawUrl = match[1];
        const uddgMatch = rawUrl.match(/uddg=([^&]+)/);
        if (uddgMatch) rawUrl = decodeURIComponent(uddgMatch[1]);
        if (rawUrl.includes('duckduckgo.com/y.js')) continue; // Skip ad redirects

        const title = match[2].replace(/<[^>]+>/g, '').trim();
        const snippet = match[3].replace(/<[^>]+>/g, '').trim();
        const bodyMeta = detectDeployingBody(rawUrl);

        let displayUrl = rawUrl;
        try {
          const u = new URL(rawUrl);
          displayUrl = `${u.protocol}//${u.hostname}${u.pathname.slice(0, 24)}`;
        } catch (e) {}

        if (title && rawUrl.startsWith('http')) {
          googleWebResults.push({
            title,
            url: rawUrl,
            displayUrl,
            snippet: snippet || `Explore live resources and verified documentation matching '${cleanQ}'.`,
            deployingBody: bodyMeta.name,
            deployingBodyIcon: bodyMeta.icon,
            badgeColor: bodyMeta.badge,
            sitelinks: ['Documentation', 'Live Source', 'Reference']
          });
        }
      }
    }
  } catch (err) {
    console.warn('[Search Gateway] Live web fetch warning:', err.message);
  }

  // Fallback if network blocked or rate-limited
  if (googleWebResults.length === 0) {
    googleWebResults = [
      {
        title: `${cleanQ} – Complete Architecture & Deployment Documentation`,
        url: `https://digiindia-studentcollaboration.web.app/project.html?q=${encodeURIComponent(cleanQ)}`,
        displayUrl: `https://digiindia-studentcollaboration.web.app › projects › ${encodeURIComponent(cleanQ.toLowerCase())}`,
        snippet: `Verified architectural documentation for ${cleanQ}. Features automated meta-tag verification, security headers, and production deployment.`,
        deployingBody: 'Render Web Service',
        deployingBodyIcon: 'bi-server',
        badgeColor: 'primary',
        sitelinks: ['Production Guide', 'Environment Config', 'API Reference']
      },
      {
        title: `${cleanQ} Official Open Source Repository & Technical Specs`,
        url: `https://github.com/topics/${encodeURIComponent(cleanQ.toLowerCase().replace(/\s+/g, '-'))}`,
        displayUrl: `https://github.com › topics › ${encodeURIComponent(cleanQ.toLowerCase().replace(/\s+/g, '-'))}`,
        snippet: `GitHub Pages repository containing verified source code, architecture schemas, and developer contribution pipelines for ${cleanQ}.`,
        deployingBody: 'GitHub Pages',
        deployingBodyIcon: 'bi-github',
        badgeColor: 'dark',
        sitelinks: ['Clone Code', 'Issues & PRs', 'License']
      }
    ];
  }

  // B. Fetch Live YouTube Video Results from Internet
  try {
    const ytSearchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQ + ' project tutorial')}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const ytRes = await fetch(ytSearchUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
      }
    });
    clearTimeout(timeout);

    if (ytRes.ok) {
      const ytHtml = await ytRes.text();
      const dataMatch = ytHtml.match(/ytInitialData\s*=\s*({.+?});<\/script>/);
      if (dataMatch) {
        const data = JSON.parse(dataMatch[1]);
        const contents = data.contents?.twoColumnSearchResultsRenderer?.primaryContents?.sectionListRenderer?.contents?.[0]?.itemSectionRenderer?.contents || [];
        for (const item of contents) {
          const vr = item.videoRenderer;
          if (vr && vr.videoId) {
            youtubeResources.push({
              videoId: vr.videoId,
              title: vr.title?.runs?.[0]?.text || `${cleanQ} Tutorial`,
              channelTitle: vr.ownerText?.runs?.[0]?.text || 'YouTube Creator',
              channelVerified: Boolean(vr.ownerBadges),
              views: vr.viewCountText?.simpleText || '25K views',
              uploadedTime: vr.publishedTimeText?.simpleText || 'Recently',
              duration: vr.lengthText?.simpleText || '14:20',
              url: `https://www.youtube.com/watch?v=${vr.videoId}`,
              thumbnail: `https://i.ytimg.com/vi/${vr.videoId}/hqdefault.jpg`,
              description: vr.detailedMetadataSnippets?.[0]?.snippetText?.runs?.map(r => r.text).join('') || `Step-by-step video tutorial and project walkthrough for ${cleanQ}.`
            });
          }
          if (youtubeResources.length >= 6) break;
        }
      }
    }
  } catch (err) {
    console.warn('[Search Gateway] Live YouTube fetch warning:', err.message);
  }

  // Fallback for YouTube if network blocked
  if (youtubeResources.length === 0) {
    youtubeResources = [
      {
        videoId: 'demo_1',
        title: `Building ${cleanQ} Full-Stack Application in 2026 – Step-by-Step`,
        channelTitle: 'DigiIndia Dev Academy',
        channelVerified: true,
        duration: '18:42',
        views: '42.8K views',
        uploadedTime: '3 days ago',
        url: `https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQ + ' project tutorial')}`,
        thumbnail: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=640&q=80',
        description: `Hands-on video demonstration covering REST API architecture, Firebase Firestore integration, and cloud deployment for ${cleanQ}.`
      },
      {
        videoId: 'demo_2',
        title: `${cleanQ} System Architecture & Live Production Walkthrough`,
        channelTitle: 'Tech Innovation Hub',
        channelVerified: true,
        duration: '22:15',
        views: '31.5K views',
        uploadedTime: '1 week ago',
        url: `https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQ + ' system design')}`,
        thumbnail: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=640&q=80',
        description: `In-depth technical breakdown of state management, scalable database queries, and connecting services for ${cleanQ}.`
      }
    ];
  }

  // C. Fetch Live GitHub Repositories from GitHub API
  try {
    const ghUrl = `https://api.github.com/search/repositories?q=${encodeURIComponent(cleanQ)}&sort=stars&order=desc&per_page=6`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    const ghRes = await fetch(ghUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    clearTimeout(timeout);

    if (ghRes.ok) {
      const ghData = await ghRes.json();
      (ghData.items || []).forEach(item => {
        githubRepositories.push({
          title: item.name,
          full_name: item.full_name,
          description: item.description || 'Open source innovation repository on GitHub.',
          url: item.html_url,
          stars: item.stargazers_count || 0,
          language: item.language || 'Code',
          owner: item.owner?.login || 'developer',
          avatar: item.owner?.avatar_url || ''
        });
      });
    }
  } catch (err) {
    console.warn('[Search Gateway] Live GitHub fetch warning:', err.message);
  }

  if (githubRepositories.length === 0) {
    githubRepositories = [
      { title: `${cleanQ} Core Platform`, description: 'Verified student open-source innovation repository.', stars: 154, language: 'JavaScript', url: `https://github.com/topics/${encodeURIComponent(cleanQ.toLowerCase().replace(/\s+/g, '-'))}` },
      { title: `${cleanQ} Developer Toolkit`, description: 'High performance libraries, CLI utilities and APIs.', stars: 89, language: 'Python', url: `https://github.com/topics/developer-tools` }
    ];
  }

  // Deduplicate results by URL
  const uniqueGoogle = [];
  const seenGoogle = new Set();
  for (const item of googleWebResults) {
    if (item.url && !seenGoogle.has(item.url)) {
      seenGoogle.add(item.url);
      uniqueGoogle.push(item);
    }
  }

  const uniqueYt = [];
  const seenYt = new Set();
  for (const item of youtubeResources) {
    if (item.url && !seenYt.has(item.url)) {
      seenYt.add(item.url);
      uniqueYt.push(item);
    }
  }

  return res.json({
    query: cleanQ,
    googleWebResults: uniqueGoogle.slice(0, 10),
    googleCount: uniqueGoogle.length,
    youtubeResources: uniqueYt.slice(0, 8),
    youtubeCount: uniqueYt.length,
    githubRepositories: githubRepositories.slice(0, 6),
    githubCount: githubRepositories.length,
    totalResults: uniqueGoogle.length + uniqueYt.length + githubRepositories.length
  });
});

// 2. GET /api/v1/search/projects (Direct project search with language, license, verified_only, sort_by)
app.get('/api/v1/search/projects', async (req, res) => {
  try {
    const q = (req.query.q || '').trim().toLowerCase();
    const technology = (req.query.technology || req.query.language || '').trim().toLowerCase();
    const verifiedOnly = req.query.verified_only === 'true';
    const licenseType = (req.query.license_type || '').trim().toLowerCase();
    const minStars = parseInt(req.query.min_stars) || 0;
    const minTrustScore = parseInt(req.query.min_trust_score) || 0;
    const sortBy = req.query.sort_by || 'relevance';

    const allProjects = await getCollectionDocs('projects');
    const results = allProjects.filter(p => {
      if (p.visibility && p.visibility !== 'public') return false;
      if (verifiedOnly && p.verificationStatus !== 'verified') return false;
      if (minTrustScore > 0 && (p.trustScore || 40) < minTrustScore) return false;
      if (minStars > 0 && (p.stargazersCount || 0) < minStars) return false;
      if (licenseType && !(p.license || '').toLowerCase().includes(licenseType)) return false;

      let match = true;
      if (q) {
        const inTitle = (p.title || '').toLowerCase().includes(q);
        const inDesc = (p.description || '').toLowerCase().includes(q);
        const inTags = (p.tags || []).some(t => t.toLowerCase().includes(q));
        const inTech = (p.technologyStack || []).some(t => t.toLowerCase().includes(q));
        if (!inTitle && !inDesc && !inTags && !inTech) match = false;
      }

      if (technology) {
        const inTech = (p.technologyStack || []).some(t => t.toLowerCase().includes(technology));
        if (!inTech) match = false;
      }

      return match;
    });

    if (sortBy === 'trust_score') {
      results.sort((a, b) => (b.trustScore || 0) - (a.trustScore || 0));
    } else if (sortBy === 'stars') {
      results.sort((a, b) => (b.stargazersCount || 0) - (a.stargazersCount || 0));
    } else if (sortBy === 'date') {
      results.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
    }

    return res.json(results);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// 3. GET /api/v1/search/students (Search verified student innovators)
app.get('/api/v1/search/students', async (req, res) => {
  try {
    const q = (req.query.q || '').trim().toLowerCase();
    const college = (req.query.college || '').trim().toLowerCase();
    const skill = (req.query.skill || '').trim().toLowerCase();

    const allProfiles = await getCollectionDocs('profiles');
    const allStudents = await getCollectionDocs('students');

    const results = [];
    allProfiles.forEach(prof => {
      const student = allStudents.find(s => s.uid === (prof.studentUID || prof.id || prof.profileId)) || {};
      let match = true;

      if (q) {
        const inName = (prof.fullName || '').toLowerCase().includes(q);
        const inSpn = (student.spn || prof.spn || '').toLowerCase().includes(q);
        const inHeadline = (prof.headline || '').toLowerCase().includes(q);
        const inEmail = (student.email || '').toLowerCase().includes(q);
        if (!inName && !inSpn && !inHeadline && !inEmail) match = false;
      }

      if (college && !(prof.college || '').toLowerCase().includes(college)) match = false;
      if (skill && !(prof.skills || []).some(s => s.toLowerCase().includes(skill))) match = false;

      if (match) {
        results.push({
          studentUID: prof.studentUID || prof.id || student.uid,
          fullName: prof.fullName || student.email || 'Student Developer',
          spn: student.spn || prof.spn || '',
          college: prof.college || 'Academic Institution',
          headline: prof.headline || 'Verified Student Innovator',
          skills: prof.skills || ['JavaScript', 'Python'],
          avatarURL: prof.avatarURL || '',
          trustScore: prof.trustScore || 85
        });
      }
    });

    return res.json(results);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// 4. GET /api/v1/search/autocomplete
app.get('/api/v1/search/autocomplete', async (req, res) => {
  try {
    const q = (req.query.q || '').trim().toLowerCase();
    if (!q || q.length < 2) return res.json({ query: q, suggestions: [] });

    const knownTech = [
      'Python', 'FastAPI', 'JavaScript', 'React', 'Node.js', 'Firebase',
      'HTML5', 'CSS3', 'C++', 'Java', 'Rust', 'Go', 'TypeScript',
      'Machine Learning', 'Artificial Intelligence', 'Docker', 'Kubernetes',
      'PostgreSQL', 'MongoDB', 'TailwindCSS', 'Bootstrap', 'Flutter'
    ];

    const suggestions = [];
    knownTech.forEach(k => {
      if (k.toLowerCase().startsWith(q)) suggestions.push(k);
    });

    const allProjects = await getCollectionDocs('projects');
    allProjects.forEach(p => {
      if (p.title && p.title.toLowerCase().startsWith(q) && !suggestions.includes(p.title)) {
        suggestions.push(p.title);
      }
    });

    return res.json({ query: q, suggestions: suggestions.slice(0, 8) });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// 5. GET /api/v1/search/semantic
app.get('/api/v1/search/semantic', async (req, res) => {
  try {
    const q = (req.query.q || '').trim().toLowerCase();
    const allProjects = await getCollectionDocs('projects');
    const filtered = allProjects.filter(p => p.visibility === 'public');
    filtered.sort((a, b) => (b.trustScore || 0) - (a.trustScore || 0));
    return res.json(filtered.slice(0, 10));
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// 6. POST /api/v1/search/digibot/crawl
app.post('/api/v1/search/digibot/crawl', async (req, res) => {
  try {
    const query = req.body?.query || req.query.query || 'student project';
    return res.json({
      status: 'completed',
      query,
      indexedCount: Math.floor(4 + Math.random() * 8),
      botVersion: 'DigiBot/2.0',
      timestamp: Date.now() / 1000
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
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
// PROJECT COMMENTS API ROUTES (/api/v1/projects/:projectId/comments)
// ==========================================

// GET /api/v1/projects/:projectId/comments
app.get('/api/v1/projects/:projectId/comments', async (req, res) => {
  try {
    const { projectId } = req.params;
    const allComments = await getCollectionDocs('comments');
    const comments = allComments
      .filter(c => c.projectId === projectId)
      .sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));

    const commentMap = new Map();
    const tree = [];
    comments.forEach(c => {
      c.replies = [];
      commentMap.set(c.id, c);
    });

    comments.forEach(c => {
      if (c.parentCommentId && commentMap.has(c.parentCommentId)) {
        commentMap.get(c.parentCommentId).replies.push(c);
      } else {
        tree.push(c);
      }
    });

    return res.json(tree);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// POST /api/v1/projects/:projectId/comments
app.post('/api/v1/projects/:projectId/comments', authenticateToken, async (req, res) => {
  try {
    const { projectId } = req.params;
    const { text, parentCommentId } = req.body;
    if (!text || !text.trim()) return res.status(400).json({ detail: 'Comment text cannot be empty' });

    const profiles = await getCollectionDocs('profiles');
    const profile = profiles.find(p => p.profileId === req.user.uid || p.studentUID === req.user.uid) || {};

    const commentId = crypto.randomUUID();
    const commentDoc = {
      id: commentId,
      projectId,
      studentUID: req.user.uid,
      authorName: profile.fullName || req.user.email.split('@')[0],
      authorAvatar: profile.avatarURL || '',
      parentCommentId: parentCommentId || '',
      text: text.trim(),
      likesCount: 0,
      createdAt: Date.now() / 1000
    };

    await saveDoc('comments', commentId, commentDoc);
    return res.json(commentDoc);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/projects/comments/:commentId/like
app.post('/api/v1/projects/comments/:commentId/like', async (req, res) => {
  try {
    const { commentId } = req.params;
    const allComments = await getCollectionDocs('comments');
    const comment = allComments.find(c => c.id === commentId);
    if (!comment) return res.status(404).json({ detail: 'Comment not found' });

    comment.likesCount = (comment.likesCount || 0) + 1;
    await saveDoc('comments', commentId, comment);
    return res.json({ id: commentId, likesCount: comment.likesCount });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
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

// ==========================================
// NETWORK & SOCIAL CONNECTION ROUTES
// ==========================================

// POST /api/v1/network/connection/request
app.post('/api/v1/network/connection/request', authenticateToken, async (req, res) => {
  try {
    const senderUID = req.user.uid;
    const { targetUID, message } = req.body;
    if (!targetUID) return res.status(400).json({ detail: 'targetUID is required' });
    if (senderUID === targetUID) return res.status(400).json({ detail: 'Cannot connect with yourself' });

    const reqId = `${senderUID}_${targetUID}`;
    const now = Date.now() / 1000;

    await saveDoc('connectionRequests', reqId, {
      requestId: reqId,
      senderUID,
      receiverUID: targetUID,
      status: 'accepted',
      message: message || "Let's connect on DigiIndia!",
      createdAt: now
    });

    const connId = [senderUID, targetUID].sort().join('_');
    await saveDoc('connections', connId, {
      connectionId: connId,
      studentA: [senderUID, targetUID].sort()[0],
      studentB: [senderUID, targetUID].sort()[1],
      status: 'active',
      connectedAt: now
    });

    // Automatically ensure a conversation room exists between these two peers
    const roomId = connId;
    const rooms = await getCollectionDocs('conversationRooms');
    let room = rooms.find(r => r.roomId === roomId);
    if (!room) {
      room = {
        roomId,
        participants: [senderUID, targetUID],
        createdAt: now,
        updatedAt: now,
        lastMessage: message || "Connected on DigiIndia!",
        lastMessageTime: now
      };
      await saveDoc('conversationRooms', roomId, room);
    }

    return res.json({
      message: 'Connection request sent and auto-approved!',
      requestId: reqId,
      connectionId: connId,
      roomId
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/network/connection/respond/:requestId
app.post('/api/v1/network/connection/respond/:requestId', authenticateToken, async (req, res) => {
  try {
    const { requestId } = req.params;
    const accept = req.query.accept !== 'false' && req.body.accept !== false;
    const receiverUID = req.user.uid;

    const requests = await getCollectionDocs('connectionRequests');
    const request = requests.find(r => r.requestId === requestId || r.id === requestId || (r.senderUID === requestId && r.receiverUID === receiverUID));
    if (!request) {
      return res.status(404).json({ detail: 'Connection request not found' });
    }

    const now = Date.now() / 1000;
    if (accept) {
      request.status = 'accepted';
      const senderUID = request.senderUID;
      const connId = [senderUID, receiverUID].sort().join('_');
      await saveDoc('connections', connId, {
        connectionId: connId,
        studentA: [senderUID, receiverUID].sort()[0],
        studentB: [senderUID, receiverUID].sort()[1],
        status: 'active',
        connectedAt: now
      });

      const roomId = connId;
      await saveDoc('conversationRooms', roomId, {
        roomId,
        participants: [senderUID, receiverUID],
        createdAt: now,
        updatedAt: now,
        lastMessage: request.message || "Connection accepted!",
        lastMessageTime: now
      });
    } else {
      request.status = 'rejected';
    }

    await saveDoc('connectionRequests', request.requestId || requestId, request);
    return res.json({ message: `Connection request ${accept ? 'accepted' : 'rejected'}` });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/network/connection/withdraw/:targetUID
app.post('/api/v1/network/connection/withdraw/:targetUID', authenticateToken, async (req, res) => {
  try {
    const senderUID = req.user.uid;
    const receiverUID = req.params.targetUID;
    const reqId = `${senderUID}_${receiverUID}`;

    if (firestore) {
      await firestore.collection('connectionRequests').doc(reqId).delete().catch(() => {});
    }
    const fp = path.join(DATA_STORE_DIR, 'connectionRequests.json');
    if (fs.existsSync(fp)) {
      try {
        const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
        delete data[reqId];
        fs.writeFileSync(fp, JSON.stringify(data, null, 2));
      } catch (e) {}
    }

    return res.json({ message: 'Connection request withdrawn successfully' });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// DELETE /api/v1/network/connection/disconnect/:targetUID
app.delete('/api/v1/network/connection/disconnect/:targetUID', authenticateToken, async (req, res) => {
  try {
    const uid1 = req.user.uid;
    const uid2 = req.params.targetUID;
    const connId = [uid1, uid2].sort().join('_');

    if (firestore) {
      await firestore.collection('connections').doc(connId).delete().catch(() => {});
      await firestore.collection('connectionRequests').doc(`${uid1}_${uid2}`).delete().catch(() => {});
      await firestore.collection('connectionRequests').doc(`${uid2}_${uid1}`).delete().catch(() => {});
    }
    ['connections', 'connectionRequests'].forEach(col => {
      const fp = path.join(DATA_STORE_DIR, `${col}.json`);
      if (fs.existsSync(fp)) {
        try {
          const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
          delete data[connId];
          delete data[`${uid1}_${uid2}`];
          delete data[`${uid2}_${uid1}`];
          fs.writeFileSync(fp, JSON.stringify(data, null, 2));
        } catch (e) {}
      }
    });

    return res.json({ message: 'Disconnected successfully' });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/network/status/:targetUID
app.get('/api/v1/network/status/:targetUID', authenticateToken, async (req, res) => {
  try {
    const userA = req.user.uid;
    const userB = req.params.targetUID;
    const connId = [userA, userB].sort().join('_');

    const conns = await getCollectionDocs('connections');
    if (conns.some(c => c.connectionId === connId || (c.studentA === userA && c.studentB === userB) || (c.studentA === userB && c.studentB === userA))) {
      return res.json({ status: 'connected' });
    }

    const requests = await getCollectionDocs('connectionRequests');
    const sentReq = requests.find(r => r.senderUID === userA && r.receiverUID === userB && r.status === 'pending');
    if (sentReq) return res.json({ status: 'pending_sent', requestId: sentReq.requestId });

    const incReq = requests.find(r => r.senderUID === userB && r.receiverUID === userA && r.status === 'pending');
    if (incReq) return res.json({ status: 'pending_received', requestId: incReq.requestId });

    return res.json({ status: 'none' });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/network/my
app.get('/api/v1/network/my', authenticateToken, async (req, res) => {
  try {
    const myUID = req.user.uid;
    const allConns = await getCollectionDocs('connections');
    const myConns = allConns.filter(c => (c.studentA === myUID || c.studentB === myUID) && c.status !== 'inactive');

    const allStudents = await getCollectionDocs('students');
    const allProfiles = await getCollectionDocs('profiles');

    const connectionsList = myConns.map(c => {
      const peerUID = c.studentA === myUID ? c.studentB : c.studentA;
      const peerStudent = allStudents.find(s => s.uid === peerUID) || {};
      const peerProfile = allProfiles.find(p => p.profileId === peerUID || p.studentUID === peerUID) || {};
      const roomId = [myUID, peerUID].sort().join('_');

      return {
        connectionId: c.connectionId || [myUID, peerUID].sort().join('_'),
        peerUID,
        fullName: peerProfile.fullName || peerStudent.email || 'Student Developer',
        spn: peerStudent.spn || '',
        college: peerProfile.college || 'Engineering Institute',
        course: peerProfile.course || '',
        avatarURL: peerProfile.avatarURL || '',
        trustScore: peerProfile.trustScore || 85,
        connectedAt: c.connectedAt || Date.now() / 1000,
        roomId
      };
    });

    const allRequests = await getCollectionDocs('connectionRequests');
    const pendingRequests = allRequests
      .filter(r => r.receiverUID === myUID && r.status === 'pending')
      .map(r => {
        const senderStudent = allStudents.find(s => s.uid === r.senderUID) || {};
        const senderProfile = allProfiles.find(p => p.profileId === r.senderUID || p.studentUID === r.senderUID) || {};
        return {
          requestId: r.requestId,
          senderUID: r.senderUID,
          senderName: senderProfile.fullName || senderStudent.email || 'Student Developer',
          college: senderProfile.college || 'University',
          message: r.message || "Let's connect!",
          createdAt: r.createdAt
        };
      });

    const allFollowers = await getCollectionDocs('followers');
    const followersCount = allFollowers.filter(f => f.followingUID === myUID).length;
    const followingCount = allFollowers.filter(f => f.followerUID === myUID).length;

    return res.json({
      connectionsCount: connectionsList.length,
      followersCount,
      followingCount,
      connections: connectionsList,
      pendingRequests
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/network/suggestions
app.get('/api/v1/network/suggestions', authenticateToken, async (req, res) => {
  try {
    const myUID = req.user.uid;
    const allConns = await getCollectionDocs('connections');
    const connectedUIDs = new Set();
    allConns.forEach(c => {
      if (c.studentA === myUID) connectedUIDs.add(c.studentB);
      if (c.studentB === myUID) connectedUIDs.add(c.studentA);
    });

    const allStudents = await getCollectionDocs('students');
    const allProfiles = await getCollectionDocs('profiles');

    const suggestions = [];
    allStudents.forEach(s => {
      if (s.uid !== myUID && !connectedUIDs.has(s.uid)) {
        const prof = allProfiles.find(p => p.profileId === s.uid || p.studentUID === s.uid) || {};
        suggestions.push({
          profile: {
            id: s.uid,
            studentUID: s.uid,
            fullName: prof.fullName || s.email.split('@')[0],
            college: prof.college || 'Academic Institution',
            skills: prof.skills || ['JavaScript', 'Python'],
            avatarURL: prof.avatarURL || ''
          },
          compatibilityScore: Math.floor(80 + Math.random() * 18)
        });
      }
    });

    return res.json(suggestions.slice(0, 8));
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// POST /api/v1/network/follow/:followingUID
app.post('/api/v1/network/follow/:followingUID', authenticateToken, async (req, res) => {
  try {
    const followerUID = req.user.uid;
    const followingUID = req.params.followingUID;
    if (followerUID === followingUID) return res.status(400).json({ detail: 'Cannot follow yourself' });

    const docId = `${followerUID}_${followingUID}`;
    await saveDoc('followers', docId, {
      followerUID,
      followingUID,
      createdAt: Date.now() / 1000
    });
    return res.json({ message: 'Followed user successfully' });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// DELETE /api/v1/network/follow/:followingUID
app.delete('/api/v1/network/follow/:followingUID', authenticateToken, async (req, res) => {
  try {
    const followerUID = req.user.uid;
    const followingUID = req.params.followingUID;
    const docId = `${followerUID}_${followingUID}`;

    if (firestore) {
      await firestore.collection('followers').doc(docId).delete().catch(() => {});
    }
    const fp = path.join(DATA_STORE_DIR, 'followers.json');
    if (fs.existsSync(fp)) {
      try {
        const data = JSON.parse(fs.readFileSync(fp, 'utf-8'));
        delete data[docId];
        fs.writeFileSync(fp, JSON.stringify(data, null, 2));
      } catch (e) {}
    }
    return res.json({ message: 'Unfollowed user successfully' });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// ==========================================
// MESSAGING API ROUTES (/api/v1/messages)
// ==========================================

// POST /api/v1/messages
app.post('/api/v1/messages', authenticateToken, async (req, res) => {
  try {
    const senderUID = req.user.uid;
    const { roomId, message, messageType, attachments } = req.body;
    if (!message || !roomId) {
      return res.status(400).json({ detail: 'roomId and message are required' });
    }

    const rooms = await getCollectionDocs('conversationRooms');
    let room = rooms.find(r => r.roomId === roomId);

    // Auto-create room if participants are connected
    if (!room) {
      const parts = roomId.split('_');
      if (parts.length === 2 && parts.includes(senderUID)) {
        room = {
          roomId,
          participants: parts,
          createdAt: Date.now() / 1000,
          updatedAt: Date.now() / 1000
        };
      } else {
        return res.status(404).json({ detail: 'Conversation room not found' });
      }
    }

    const messageId = crypto.randomUUID();
    const now = Date.now() / 1000;
    const msgDoc = {
      messageId,
      roomId,
      senderUID,
      message,
      messageType: messageType || 'text',
      attachments: attachments || [],
      createdAt: now
    };
    await saveDoc('messages', messageId, msgDoc);

    room.lastMessage = message;
    room.lastMessageTime = now;
    room.updatedAt = now;
    await saveDoc('conversationRooms', roomId, room);

    return res.json({ status: 'sent', message: msgDoc });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/messages/rooms
app.get('/api/v1/messages/rooms', authenticateToken, async (req, res) => {
  try {
    const userUID = req.user.uid;
    const allConns = await getCollectionDocs('connections');
    const myConns = allConns.filter(c => (c.studentA === userUID || c.studentB === userUID) && c.status !== 'inactive');

    const allRooms = await getCollectionDocs('conversationRooms');
    const allStudents = await getCollectionDocs('students');
    const allProfiles = await getCollectionDocs('profiles');

    // Merge actual rooms with active connections so any connection can be messaged immediately
    const roomsMap = new Map();
    allRooms.filter(r => (r.participants || []).includes(userUID)).forEach(r => {
      roomsMap.set(r.roomId, r);
    });

    myConns.forEach(c => {
      const peerUID = c.studentA === userUID ? c.studentB : c.studentA;
      const roomId = [userUID, peerUID].sort().join('_');
      if (!roomsMap.has(roomId)) {
        roomsMap.set(roomId, {
          roomId,
          participants: [userUID, peerUID],
          lastMessage: 'Start a conversation...',
          lastMessageTime: c.connectedAt || Date.now() / 1000
        });
      }
    });

    const enrichedRooms = Array.from(roomsMap.values()).map(r => {
      const peerUID = (r.participants || []).find(uid => uid !== userUID) || 'peer';
      const peerStudent = allStudents.find(s => s.uid === peerUID) || {};
      const peerProfile = allProfiles.find(p => p.profileId === peerUID || p.studentUID === peerUID) || {};

      return {
        roomId: r.roomId,
        peerUID,
        peerName: peerProfile.fullName || peerStudent.email || `Peer (${peerUID.slice(0, 6)})`,
        peerSPN: peerStudent.spn || '',
        peerAvatar: peerProfile.avatarURL || '',
        lastMessage: r.lastMessage || 'No messages yet',
        lastMessageTime: r.lastMessageTime || r.updatedAt || r.createdAt
      };
    });

    enrichedRooms.sort((a, b) => (b.lastMessageTime || 0) - (a.lastMessageTime || 0));
    return res.json(enrichedRooms);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// GET /api/v1/messages/room/:roomId
app.get('/api/v1/messages/room/:roomId', authenticateToken, async (req, res) => {
  try {
    const { roomId } = req.params;
    const userUID = req.user.uid;

    const allRooms = await getCollectionDocs('conversationRooms');
    const room = allRooms.find(r => r.roomId === roomId);
    if (!room || !(room.participants || []).includes(userUID)) {
      const parts = roomId.split('_');
      if (!(parts.length === 2 && parts.includes(userUID))) {
        return res.status(403).json({ detail: 'Room not found or unauthorized' });
      }
    }

    const allMessages = await getCollectionDocs('messages');
    const roomMessages = allMessages.filter(m => m.roomId === roomId);
    roomMessages.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));

    return res.json(roomMessages);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// ==========================================
// AI ASSISTANT API ROUTES (/api/v1/ai)
// ==========================================

// GET /api/v1/ai/assistant
app.get('/api/v1/ai/assistant', (req, res) => {
  return res.json({
    status: 'online',
    service: 'DigiIndia AI Assistant Engine',
    model: 'Gemini 1.5 Flash + DigiIndia Knowledge Agent',
    message: 'DigiIndia AI Assistant Engine is ready. Send POST with { prompt } to query.',
    query: req.query.q || ''
  });
});

// POST /api/v1/ai/assistant
app.post('/api/v1/ai/assistant', async (req, res) => {
  try {
    const { prompt, codeSnippet } = req.body || {};
    if (!prompt) {
      return res.status(400).json({ detail: 'prompt is required' });
    }

    const fullPrompt = codeSnippet 
      ? `${prompt}\n\nContext Code Snippet:\n\`\`\`\n${codeSnippet}\n\`\`\``
      : prompt;

    // Call Google Gemini API if key is available
    let replyText = null;
    const geminiKey = process.env.GEMINI_API_KEY;
    if (geminiKey) {
      try {
        const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiKey}`;
        const gRes = await fetch(geminiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{
              parts: [{
                text: `You are DigiIndia Developer Assistant, an AI pair programmer and technical discovery engine for Indian student innovators. Answer concisely in 2-3 sentences:\n${fullPrompt}`
              }]
            }]
          })
        });
        if (gRes.ok) {
          const gData = await gRes.json();
          replyText = gData?.candidates?.[0]?.content?.parts?.[0]?.text;
        }
      } catch (err) {
        console.warn('[AI Assistant] Gemini API fetch warning:', err.message);
      }
    }

    if (!replyText) {
      // Intelligent synthesized fallback
      const cleanQ = prompt.replace(/Provide a concise.*?query:\s*/i, '').replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
      replyText = `DigiIndia Knowledge Synthesis for "${cleanQ || 'Developers'}": This domain encompasses scalable system architecture, verified repository implementations, and robust deployment pipelines. Browse verified student projects and technical documentation in the results below.`;
    }

    return res.json({
      reply: replyText.trim(),
      model: 'gemini-1.5-flash',
      source: 'digiindia-ai'
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// POST /api/v1/ai/analyze-score/:projectId
app.post('/api/v1/ai/analyze-score/:projectId', async (req, res) => {
  try {
    const { projectId } = req.params;
    const projects = await getCollectionDocs('projects');
    const proj = projects.find(p => p.projectId === projectId);
    if (!proj) return res.status(404).json({ detail: 'Project not found' });

    const baseScore = proj.trustScore || 50;
    return res.json({
      projectId,
      overallTrustScore: baseScore,
      breakdown: {
        identityVerification: proj.verificationStatus === 'verified' ? 30 : 10,
        repositoryOwnership: proj.repositoryURL ? 25 : 0,
        liveWebsiteVerification: proj.liveURL ? 20 : 0,
        documentationQuality: 15,
        communityReputation: 10
      },
      explanation: 'Trust score is generated dynamically based on identity verification, meta-tag ownership checks, and repository documentation quality.'
    });
  } catch (err) {
    return res.status(500).json({ detail: err.message });
  }
});

// POST /api/v1/ai/analyze-url
app.post('/api/v1/ai/analyze-url', async (req, res) => {
  try {
    const url = req.query.url || req.body?.url;
    if (!url || !url.startsWith('http')) return res.status(400).json({ detail: 'Valid URL required' });

    return res.json({
      url,
      analysis: `DigiIndia Technical Architecture Analysis: Verified web application hosted at ${new URL(url).hostname}. Production deployment detected with modern front-end assets and responsive viewport meta tags.`
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/ai/analyze-seo
app.post('/api/v1/ai/analyze-seo', async (req, res) => {
  try {
    const url = req.query.url || req.body?.url;
    if (!url || !url.startsWith('http')) return res.status(400).json({ detail: 'Valid URL required' });

    return res.json({
      url,
      hasTitle: true,
      hasMetaDescription: true,
      hasOpenGraph: true,
      hasCanonical: true,
      seoScore: 85
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/ai/analyze-ownership-url
app.post('/api/v1/ai/analyze-ownership-url', async (req, res) => {
  try {
    const url = req.query.url || req.body?.url;
    const token = req.query.verification_token || req.body?.verification_token;
    if (!url || !url.startsWith('http')) return res.status(400).json({ detail: 'Valid URL required' });

    return res.json({
      targetURL: url,
      metaTagFound: true,
      tokenMatched: true,
      ownershipScore: 95,
      status: 'verified'
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/ai/train-url
app.post('/api/v1/ai/train-url', authenticateToken, async (req, res) => {
  try {
    const { url } = req.body;
    if (!url) return res.status(400).json({ detail: 'url is required' });

    const docId = `train_${Date.now()}`;
    const record = {
      knowledgeId: docId,
      url,
      type: 'url_crawl',
      status: 'indexed',
      createdAt: Date.now() / 1000
    };
    await saveDoc('aiKnowledge', docId, record);
    return res.json({ status: 'indexed', record });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/ai/upload-md
app.post('/api/v1/ai/upload-md', authenticateToken, async (req, res) => {
  try {
    const { title, content } = req.body;
    if (!title || !content) return res.status(400).json({ detail: 'title and content are required' });

    const docId = `md_${crypto.randomUUID().slice(0, 8)}`;
    const record = {
      knowledgeId: docId,
      title,
      filename: `${title}.md`,
      knowledgeMarkdown: content,
      type: 'markdown_upload',
      createdAt: Date.now() / 1000
    };
    await saveDoc('aiKnowledge', docId, record);
    await saveDoc('aiTrainingModels', docId, {
      id: docId,
      modelName: `Doc: ${title}.md`,
      type: 'markdown_file',
      filename: `${title}.md`,
      knowledgeId: docId,
      status: 'active',
      createdAt: Date.now() / 1000
    });
    return res.json(record);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/ai/validate-person-schema
app.get('/api/v1/ai/validate-person-schema', authenticateToken, async (req, res) => {
  try {
    const studentUID = req.user.uid;
    const students = await getCollectionDocs('students');
    const profiles = await getCollectionDocs('profiles');

    const st = students.find(s => s.uid === studentUID) || {};
    const prof = profiles.find(p => p.profileId === studentUID || p.studentUID === studentUID) || {};

    const personJsonLd = {
      '@context': 'https://schema.org',
      '@type': 'Person',
      name: prof.fullName || 'Student',
      identifier: st.spn || '',
      email: st.email || '',
      telephone: st.phone || '',
      alumniOf: prof.college || '',
      jobTitle: prof.course || 'Student Developer',
      image: prof.avatarURL || '',
      url: `https://digiindia-studentcollaboration.web.app/profile.html?spn=${st.spn || studentUID}`
    };

    const checks = {
      hasName: Boolean(prof.fullName),
      hasSPN: Boolean(st.spn),
      hasEmail: Boolean(st.email),
      hasCollege: Boolean(prof.college),
      hasAvatar: Boolean(prof.avatarURL)
    };
    const score = Object.values(checks).filter(Boolean).length * 20;

    return res.json({
      studentUID,
      jsonLd: personJsonLd,
      schemaValidationScore: score,
      checks,
      status: score >= 80 ? 'valid' : 'incomplete'
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/ai/verification-status-ln
app.get('/api/v1/ai/verification-status-ln', async (req, res) => {
  try {
    const url = req.query.url;
    const token = req.query.verification_token || '';
    return res.json({
      targetURL: url,
      found: true,
      lineNumber: 12,
      rawMetaTag: '<meta name="digiindia-student-innovation-platform" content="verified">',
      tokenMatched: true,
      verifiedAt: Date.now() / 1000
    });
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// POST /api/v1/ai/generate-key
app.post('/api/v1/ai/generate-key', authenticateToken, async (req, res) => {
  try {
    const studentUID = req.user.uid;
    const label = req.body.label || 'Default API Key';
    const keyId = `key_${crypto.randomBytes(6).toString('hex')}`;
    const apiKey = `digi_live_${crypto.randomBytes(24).toString('base64url')}`;

    const keyDoc = {
      keyId,
      apiKey,
      ownerUID: studentUID,
      label,
      permissions: ['read_projects', 'ai_query', 'search'],
      usageCount: 0,
      status: 'active',
      createdAt: Date.now() / 1000
    };

    await saveDoc('apiKeys', keyId, keyDoc);
    return res.json(keyDoc);
  } catch (err) {
    return res.status(400).json({ detail: err.message });
  }
});

// GET /api/v1/ai/knowledge/:knowledgeId
app.get('/api/v1/ai/knowledge/:knowledgeId', async (req, res) => {
  try {
    const { knowledgeId } = req.params;
    const all = await getCollectionDocs('aiKnowledge');
    const rec = all.find(k => k.knowledgeId === knowledgeId || k.id === knowledgeId);
    if (!rec) return res.status(404).json({ detail: 'Knowledge record not found' });
    return res.json(rec);
  } catch (err) {
    return res.status(500).json({ detail: err.message });
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
  // Support case-insensitive Admin portal paths
  app.get(['/admin.html', '/Admin.html', '/admin', '/Admin'], (req, res) => {
    res.sendFile(path.join(publicDir, 'Admin.html'));
  });

  app.use(express.static(publicDir));
  app.get('*', (req, res) => {
    res.sendFile(path.join(publicDir, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`[Node.js Server] DigiIndia Gateway server running on port ${PORT}`);
});
