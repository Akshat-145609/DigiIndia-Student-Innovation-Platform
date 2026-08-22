import random
import time
import uuid
import datetime
import hashlib
import jwt
from passlib.context import CryptContext
from config import settings
from api.providers.firebase import FirestoreRepository, FirebaseProvider
from api.providers.brevo import BrevoEmailProvider
from models.schemas import StudentRegisterSchema, LoginSchema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

students_repo = FirestoreRepository("students")
profiles_repo = FirestoreRepository("profiles")
otps_repo = FirestoreRepository("otpVerifications")

class AuthService:

    @staticmethod
    def generate_spn() -> str:
        """Generates an 8-digit unique Student Portal Number: YY + 6 random digits"""
        year_prefix = str(datetime.datetime.now().year)[-2:] # e.g. '26'
        while True:
            random_digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
            spn = f"{year_prefix}{random_digits}"
            existing = students_repo.query(filters=[("spn", "==", spn)])
            if not existing:
                return spn

    @staticmethod
    def _prepare_password(password: str, pepper: str = None) -> str:
        p = pepper if pepper is not None else settings.PASSWORD_PEPPER
        salted = f"{password}{p}"
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()

    @classmethod
    def hash_password(cls, password: str) -> str:
        prep = cls._prepare_password(password)[:72]
        try:
            return pwd_context.hash(prep)
        except Exception:
            return pwd_context.hash(password[:72])

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        if not plain_password or not hashed_password:
            return False
        
        # Candidate peppers to attempt in order
        peppers_to_try = [
            settings.PASSWORD_PEPPER,
            "hGhdbw8FdCjWuqRFlF3EyY5VohMf3Thvof864WMrBKo",
            ""
        ]
        
        # Deduplicate while preserving order
        seen = set()
        peppers = [p for p in peppers_to_try if not (p in seen or seen.add(p))]

        # 1. Try verify with candidate peppers
        for pepper in peppers:
            try:
                prep = cls._prepare_password(plain_password, pepper)[:72]
                if pwd_context.verify(prep, hashed_password):
                    return True
            except Exception:
                pass

        # 2. Try direct verify with raw password truncated to 72 bytes
        try:
            raw_pwd = plain_password[:72]
            if pwd_context.verify(raw_pwd, hashed_password):
                return True
        except Exception:
            pass

        # 3. Fallback direct equality check
        if plain_password == hashed_password:
            return True

        return False



    @staticmethod
    def create_jwt_token(uid: str, email: str, role: str = "student") -> str:
        payload = {
            "uid": uid,
            "email": email,
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    @classmethod
    def register_student(cls, schema: StudentRegisterSchema):
        # Check existing email
        existing = students_repo.query(filters=[("email", "==", schema.email)])
        if existing:
            raise Exception("Student with this email already exists")

        # Generate unique SPN
        spn = cls.generate_spn()
        uid = str(uuid.uuid4())
        hashed_password = cls.hash_password(schema.password)

        role = "admin" if schema.email.lower() == settings.ADMIN_EMAIL.lower() else "student"

        student_doc = {
            "uid": uid,
            "spn": spn,
            "email": schema.email,
            "phone": schema.phone,
            "whatsapp": schema.whatsapp or schema.phone,
            "passwordHash": hashed_password,
            "role": role,
            "status": "active",
            "verificationStatus": "pending",
            "securityEmail": schema.securityEmail or "",
            "createdAt": time.time(),
            "updatedAt": time.time()
        }
        students_repo.set(uid, student_doc)

        profile_doc = {
            "profileId": uid,
            "studentUID": uid,
            "spn": spn,
            "fullName": schema.fullName,
            "college": schema.college,
            "course": schema.course,
            "semester": schema.semester,
            "graduationYear": schema.graduationYear,
            "skills": schema.skills or [],
            "socialLinks": schema.socialLinks or {},
            "avatarURL": schema.avatarURL or "",
            "coverURL": schema.coverURL or "",
            "trustScore": 40,
            "visibility": "public",
            "createdAt": time.time()
        }
        profiles_repo.set(uid, profile_doc)

        # Send welcome email via Brevo REST API
        try:
            BrevoEmailProvider.send_welcome_email(schema.email, schema.fullName, spn)
        except Exception as e:
            pass

        token = cls.create_jwt_token(uid, schema.email, role)
        return {
            "student": {
                "uid": uid,
                "spn": spn,
                "email": schema.email,
                "fullName": schema.fullName,
                "role": role
            },
            "token": token
        }

    @classmethod
    def login(cls, schema: LoginSchema):
        identifier = schema.identifier.strip()
        target = identifier.lower()
        student = None

        # Fetch all student records across Firestore and local store
        all_students = students_repo.query(limit=500)
        
        # 1. Search for matching SPN, Email, SecurityEmail, Phone, or UID
        for s in all_students:
            spn = str(s.get("spn", "")).strip().lower()
            email = str(s.get("email", "")).strip().lower()
            sec_email = str(s.get("securityEmail", "")).strip().lower()
            phone = str(s.get("phone", "")).strip().lower()
            uid = str(s.get("uid", "")).strip().lower()

            if target in [spn, email, sec_email, phone, uid]:
                student = s
                break

        # Check for Super Admin bypass login
        is_admin_id = (target == settings.ADMIN_EMAIL.lower() or (student and student.get("role") == "admin"))
        if is_admin_id:
            if schema.password == settings.ADMIN_PASSWORD or (student and cls.verify_password(schema.password, student.get("passwordHash", ""))):
                uid = student["uid"] if student else "admin_super_uid"
                spn = student.get("spn", "26360087") if student else "26360087"
                email = student.get("email", settings.ADMIN_EMAIL) if student else settings.ADMIN_EMAIL
                token = cls.create_jwt_token(uid, email, "admin")
                return {
                    "student": {
                        "uid": uid,
                        "spn": spn,
                        "email": email,
                        "fullName": settings.ADMIN_NAME,
                        "role": "admin"
                    },
                    "token": token
                }

        if not student:
            raise Exception("Invalid SPN/Email or password")

        if not cls.verify_password(schema.password, student.get("passwordHash", "")):
            raise Exception("Invalid SPN/Email or password")

        uid = student["uid"]
        profile = profiles_repo.get(uid) or {}
        role = student.get("role", "student")
        if student.get("email", "").lower() == settings.ADMIN_EMAIL.lower():
            role = "admin"

        token = cls.create_jwt_token(uid, student["email"], role)
        return {
            "student": {
                "uid": uid,
                "spn": student.get("spn", ""),
                "email": student["email"],
                "fullName": profile.get("fullName", student.get("email", "").split("@")[0]),
                "role": role
            },
            "token": token
        }


    @classmethod
    def request_otp(cls, email: str, name: str = "Student"):
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = time.time() + (settings.OTP_EXPIRY_MINUTES * 60)
        
        otps_repo.set(email, {
            "email": email,
            "otp": otp_code,
            "expiresAt": expires_at,
            "createdAt": time.time()
        })

        # Send via Brevo REST
        res = BrevoEmailProvider.send_otp_email(email, name, otp_code)
        return {"message": f"OTP sent to {email}", "expiryMinutes": settings.OTP_EXPIRY_MINUTES}

    @classmethod
    def verify_otp(cls, email: str, otp: str):
        record = otps_repo.get(email)
        if not record:
            raise Exception("No OTP request found for this email")
        if time.time() > record.get("expiresAt", 0):
            raise Exception("OTP has expired. Please request a new one.")
        if record.get("otp") != otp:
            raise Exception("Invalid OTP code")

        otps_repo.delete(email)
        return {"message": "OTP verified successfully", "verified": True}

    @classmethod
    def request_password_reset_otp(cls, identifier: str):
        ident = identifier.strip()
        student = None
        if len(ident) == 8 and ident.isdigit():
            res = students_repo.query(filters=[("spn", "==", ident)])
            if res: student = res[0]
        else:
            res = students_repo.query(filters=[("email", "==", ident)])
            if res: student = res[0]

        if not student:
            raise Exception("No student account found matching the provided Primary Email or 8-digit SPN")


        target_email = student.get("email")
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = time.time() + (settings.OTP_EXPIRY_MINUTES * 60)

        otps_repo.set(target_email, {
            "email": target_email,
            "otp": otp_code,
            "uid": student["uid"],
            "type": "password_reset",
            "expiresAt": expires_at,
            "createdAt": time.time()
        })

        profile = profiles_repo.get(student["uid"]) or {}
        fullName = profile.get("fullName", "Student")

        # Send via Brevo REST API to primary email & security email
        try:
            BrevoEmailProvider.send_otp_email(target_email, fullName, otp_code)
            if student.get("securityEmail"):
                BrevoEmailProvider.send_otp_email(student["securityEmail"], fullName, otp_code)
        except Exception:
            pass

        return {
            "message": f"Multi-Factor OTP sent to {target_email} and security email.",
            "email": target_email,
            "spn": student["spn"]
        }

    @classmethod
    def reset_password_with_otp(cls, identifier: str, otp: str, new_password: str):
        if len(new_password) < 6:
            raise Exception("New password must be at least 6 characters long")

        ident = identifier.strip()
        student = None
        if len(ident) == 8 and ident.isdigit():
            res = students_repo.query(filters=[("spn", "==", ident)])
            if res: student = res[0]
        else:
            res = students_repo.query(filters=[("email", "==", ident)])
            if not res:
                res = students_repo.query(filters=[("securityEmail", "==", ident)])
            if res: student = res[0]

        if not student:
            raise Exception("Invalid SPN or Email")

        target_email = student.get("email")
        record = otps_repo.get(target_email)
        if not record:
            raise Exception("No active password reset request found. Request a new OTP.")

        if time.time() > record.get("expiresAt", 0):
            raise Exception("OTP has expired. Please request a new one.")

        if record.get("otp") != otp:
            raise Exception("Invalid OTP verification code")

        # Hash and update password
        hashed_password = cls.hash_password(new_password)
        student["passwordHash"] = hashed_password
        student["updatedAt"] = time.time()
        students_repo.set(student["uid"], student)

        otps_repo.delete(target_email)

        return {"message": "Password reset successfully! You can now log in with your new password.", "status": "success"}

