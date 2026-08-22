from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any

class StudentRegisterSchema(BaseModel):
    fullName: str
    email: EmailStr
    phone: str
    whatsapp: Optional[str] = None
    password: str
    securityEmail: Optional[EmailStr] = None
    college: str
    course: str
    semester: Optional[str] = "1"
    graduationYear: Optional[str] = "2027"
    abcId: Optional[str] = None
    aadhaar: Optional[str] = None
    socialLinks: Optional[Dict[str, str]] = {}
    skills: Optional[List[str]] = []
    avatarURL: Optional[str] = None
    coverURL: Optional[str] = None

class LoginSchema(BaseModel):
    identifier: str # Can be SPN or Email
    password: str

class OTPRequestSchema(BaseModel):
    email: EmailStr
    name: Optional[str] = "Student"

class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp: str

class ProfileUpdateSchema(BaseModel):
    fullName: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    college: Optional[str] = None
    course: Optional[str] = None
    semester: Optional[str] = None
    graduationYear: Optional[str] = None
    skills: Optional[List[str]] = None
    socialLinks: Optional[Dict[str, str]] = None
    visibility: Optional[str] = "public"
    avatarURL: Optional[str] = None
    coverURL: Optional[str] = None


class ProjectCreateSchema(BaseModel):
    title: str
    description: str
    repositoryURL: str
    liveURL: Optional[str] = ""
    visibility: Optional[str] = "public"
    technologyStack: Optional[List[str]] = []
    category: Optional[str] = "Software"
    license: Optional[str] = "MIT"
    tags: Optional[List[str]] = []

class ProjectUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    repositoryURL: Optional[str] = None
    liveURL: Optional[str] = None
    visibility: Optional[str] = None
    technologyStack: Optional[List[str]] = None
    category: Optional[str] = None
    license: Optional[str] = None
    tags: Optional[List[str]] = None


class ProjectVerifyRequestSchema(BaseModel):
    projectId: str
    verificationMethod: Optional[str] = "meta_tag"

class APIKeyCreateSchema(BaseModel):
    apiName: str
    permissions: Optional[List[str]] = ["search", "projects"]
    expiresInDays: Optional[int] = 365

class ConnectionRequestSchema(BaseModel):
    targetUID: str
    message: Optional[str] = ""

class MessageSendSchema(BaseModel):
    roomId: str
    message: str
    messageType: Optional[str] = "text"
    attachments: Optional[List[str]] = []

class AIReviewRequestSchema(BaseModel):
    projectId: Optional[str] = None
    codeSnippet: Optional[str] = None
    language: Optional[str] = "python"
    prompt: Optional[str] = None

class AdminUserUpdateSchema(BaseModel):
    studentUID: str
    role: Optional[str] = None
    verificationStatus: Optional[str] = None
    status: Optional[str] = None
