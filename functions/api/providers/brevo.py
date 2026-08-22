import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

class BrevoEmailProvider:
    """
    Brevo Transactional Email Service Provider via REST API.
    Sends raw HTTPS POST requests to https://api.brevo.com/v3/smtp/email
    """
    BASE_URL = "https://api.brevo.com/v3"

    @classmethod
    def send_email(cls, recipient_email: str, recipient_name: str, subject: str, html_content: str, text_content: str = None, template_id: int = None, params: dict = None):
        if not settings.ENABLE_EMAIL:
            logger.info(f"Email disabled via feature flag. Skipping email to {recipient_email}")
            return {"status": "skipped", "message": "Email sending disabled"}

        if not settings.BREVO_API_KEY:
            logger.warning("BREVO_API_KEY is missing. Email skipped.")
            return {"status": "error", "message": "BREVO_API_KEY missing"}

        url = f"{cls.BASE_URL}/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }

        payload = {
            "sender": {
                "name": settings.BREVO_SENDER_NAME,
                "email": settings.BREVO_SENDER_EMAIL
            },
            "to": [
                {
                    "email": recipient_email,
                    "name": recipient_name or recipient_email
                }
            ],
            "subject": subject
        }

        if template_id:
            payload["templateId"] = template_id
            if params:
                payload["params"] = params
        else:
            payload["htmlContent"] = html_content
            if text_content:
                payload["textContent"] = text_content

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Email sent successfully to {recipient_email}. MessageID: {response.json().get('messageId')}")
                    return {"status": "success", "data": response.json()}
                else:
                    logger.error(f"Brevo API error ({response.status_code}): {response.text}")
                    return {"status": "failed", "error": response.text, "code": response.status_code}
        except Exception as e:
            logger.error(f"Exception sending email via Brevo REST API: {e}")
            return {"status": "error", "message": str(e)}

    @classmethod
    def send_otp_email(cls, recipient_email: str, recipient_name: str, otp_code: str):
        subject = "Your DigiIndia Verification OTP Code"
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <h2 style="color: #0D6EFD; margin-bottom: 10px;">DigiIndia Verification</h2>
                <p style="color: #333; font-size: 15px;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Use the following One-Time Password (OTP) to complete your identity/email verification. This code is valid for <strong>{settings.OTP_EXPIRY_MINUTES} minutes</strong>.</p>
                <div style="text-align: center; margin: 25px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #6610F2; background: #EFE8FF; padding: 10px 25px; border-radius: 8px;">{otp_code}</span>
                </div>
                <p style="color: #888; font-size: 12px;">If you did not request this OTP, please ignore this message or report suspicious activity to support.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin-top: 25px;">
                <p style="color: #aaa; font-size: 11px; text-align: center;">DigiIndia – Student Innovation Platform © 2026</p>
            </div>
        </div>
        """
        return cls.send_email(recipient_email, recipient_name, subject, html_content)

    @classmethod
    def send_account_activation_email(cls, recipient_email: str, recipient_name: str, spn: str, activation_token: str, otp_code: str, secondary_email: str = None):
        subject = "Activate Your DigiIndia Student Account & Verification OTP"
        activation_link = f"http://localhost:8000/activate.html?token={activation_token}&spn={spn}"
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border-top: 4px solid #0D6EFD;">
                <h2 style="color: #0D6EFD; margin-top: 0;">DigiIndia Student Activation 🚀</h2>
                <p style="color: #333;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Welcome to DigiIndia! Your unique Student Portal Number (SPN) is: <strong style="color: #6610F2;">{spn}</strong></p>
                <p style="color: #555;">Use the OTP below or click the activation link to activate your student workspace:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #0D6EFD; background: #E7F1FF; padding: 10px 20px; border-radius: 8px;">{otp_code}</span>
                </div>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{activation_link}" style="background: linear-gradient(135deg, #0D6EFD, #6610F2); color: white; padding: 12px 28px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Activate Student Account</a>
                </div>
                <p style="color: #777; font-size: 13px;">Recovery / Security Email linked: <strong>{secondary_email or 'None'}</strong></p>
                <hr style="border: none; border-top: 1px solid #eee; margin-top: 25px;">
                <p style="color: #aaa; font-size: 11px; text-align: center;">DigiIndia Student Innovation Platform © 2026</p>
            </div>
        </div>
        """
        res = cls.send_email(recipient_email, recipient_name, subject, html_content)
        if secondary_email and secondary_email != recipient_email:
            cls.send_email(secondary_email, recipient_name, f"[Security Notice] {subject}", html_content)
        return res

    @classmethod
    def send_project_upload_email(cls, recipient_email: str, recipient_name: str, project_title: str, project_id: str, verification_token: str):
        subject = f"Project Registered: {project_title} – Next Steps for Ownership Verification"
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border-top: 4px solid #198754;">
                <h2 style="color: #198754; margin-top: 0;">Project Uploaded Successfully! 🎉</h2>
                <p style="color: #333;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Your project <strong>"{project_title}"</strong> has been successfully registered in the DigiIndia Student Innovation Repository.</p>
                <div style="background: #E8F5E9; border-left: 4px solid #198754; padding: 15px; border-radius: 6px; margin: 20px 0;">
                    <p style="margin: 0; color: #1B5E20; font-weight: bold;">Verification Meta Tag:</p>
                    <code style="display: block; background: #ffffff; padding: 8px; border-radius: 4px; margin-top: 6px; word-break: break-all; color: #0D6EFD;">&lt;meta name="digiindia-student-innovation-platform" content="{verification_token}"&gt;</code>
                </div>
                <p style="color: #555;">Add this meta tag to your live website `<head>` section or repository `README.md` file to verify project ownership and boost your Trust Score to 85+!</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="http://localhost:8000/dashboard.html" style="background: #198754; color: white; padding: 12px 28px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Go to Dashboard</a>
                </div>
            </div>
        </div>
        """
        return cls.send_email(recipient_email, recipient_name, subject, html_content)

    @classmethod
    def send_verification_pending_email(cls, recipient_email: str, recipient_name: str, project_title: str, days_pending: int, reminder_count: int = 1):
        subject = f"Action Required: Verify ownership for '{project_title}' (Day {days_pending} Reminder)"
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border-top: 4px solid #FFC107;">
                <h2 style="color: #D39E00; margin-top: 0;">Project Verification Pending ⏳</h2>
                <p style="color: #333;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Your project <strong>"{project_title}"</strong> has been waiting for ownership verification for <strong>{days_pending} days</strong>.</p>
                <p style="color: #555;">Verified projects gain priority ranking on the DigiIndia Search Engine and unlock developer API access!</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="http://localhost:8000/dashboard.html" style="background: #FFC107; color: #212529; padding: 12px 28px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Verify Project Now</a>
                </div>
                <p style="color: #888; font-size: 12px;">Next automated reminder scheduled based on formula: Day_n = 3 * 2^(n-1).</p>
            </div>
        </div>
        """
        return cls.send_email(recipient_email, recipient_name, subject, html_content)

    @classmethod
    def send_verification_success_email(cls, recipient_email: str, recipient_name: str, project_title: str, trust_score: int):
        subject = f"Congratulations! Project Verified: '{project_title}'"
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border-top: 4px solid #0D6EFD;">
                <h2 style="color: #0D6EFD; margin-top: 0;">Verification Confirmed! ✅</h2>
                <p style="color: #333;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Ownership of project <strong>"{project_title}"</strong> has been successfully verified by DigiIndia Python Web Crawler!</p>
                <div style="background: #E7F1FF; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <span style="font-size: 14px; color: #084298; display: block;">Updated Student Trust Score:</span>
                    <span style="font-size: 36px; font-weight: bold; color: #0D6EFD;">{trust_score} / 100</span>
                </div>
            </div>
        </div>
        """
        return cls.send_email(recipient_email, recipient_name, subject, html_content)

    @classmethod
    def send_project_analytics_email(cls, recipient_email: str, recipient_name: str, project_title: str, stats: dict):
        subject = f"Monthly Innovation Analytics Report for '{project_title}'"
        coupon_code = stats.get("shareCouponCode", f"DIGI-{project_title[:4].upper()}-2026")
        html_content = f"""
        <div style="font-family: 'Poppins', sans-serif; padding: 20px; background-color: #f4f6f9;">
            <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border-top: 4px solid #6610F2;">
                <h2 style="color: #6610F2; margin-top: 0;">Project Performance & Engagement 📈</h2>
                <p style="color: #333;">Hello <strong>{recipient_name}</strong>,</p>
                <p style="color: #555;">Here is your real-time analytics report for <strong>"{project_title}"</strong>:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background: #F8F9FA;"><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Search Appearances:</td><td style="padding: 10px; border: 1px solid #ddd; color: #0D6EFD; font-weight: bold;">{stats.get('searchAppearances', 0)}</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Click-Through Rate (CTR):</td><td style="padding: 10px; border: 1px solid #ddd; color: #198754; font-weight: bold;">{stats.get('ctr', '4.8%')}</td></tr>
                    <tr style="background: #F8F9FA;"><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Likes / Appreciations:</td><td style="padding: 10px; border: 1px solid #ddd;">{stats.get('likes', 0)}</td></tr>
                    <tr><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Comments & Feedback:</td><td style="padding: 10px; border: 1px solid #ddd;">{stats.get('comments', 0)}</td></tr>
                    <tr style="background: #F8F9FA;"><td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Unique Share Coupon Code:</td><td style="padding: 10px; border: 1px solid #ddd; font-family: monospace; color: #6610F2; font-weight: bold;">{coupon_code}</td></tr>
                </table>
            </div>
        </div>
        """
        return cls.send_email(recipient_email, recipient_name, subject, html_content)

