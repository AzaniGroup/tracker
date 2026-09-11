import logging
import resend
from django.conf import settings

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Masks an email address for privacy (e.g. dama@azanigroup.com.ng -> d**a@azanigroup.com.ng)."""
    if not email or '@' not in email:
        return email or ''
    user_part, domain_part = email.split('@', 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + '***'
    else:
        masked_user = user_part[0] + '*' * (len(user_part) - 2) + user_part[-1]
    return f"{masked_user}@{domain_part}"


def send_resend_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> dict:
    """
    Sends an email using the Resend Python SDK.
    Falls back to console/logger if RESEND_API_KEY is not configured.
    """
    api_key = getattr(settings, 'RESEND_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Azani Logistics <onboarding@resend.dev>')

    if not api_key:
        logger.warning(
            f"[RESEND NOT CONFIGURED] Simulated email to '{to_email}' with subject '{subject}'.\n"
            f"Content: {text_content or html_content}"
        )
        print(f"\n=======================================================")
        print(f"[RESEND SIMULATION] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{text_content or html_content}")
        print(f"=======================================================\n")
        return {"id": "simulated", "status": "simulated"}

    resend.api_key = api_key

    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    if text_content:
        params["text"] = text_content

    try:
        response = resend.Emails.send(params)
        logger.info(f"Resend email sent successfully to {to_email}. Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to send email via Resend to {to_email}: {e}")
        # Log to console for quick troubleshooting during development
        print(f"[RESEND ERROR] Failed to send email to {to_email}: {e}")
        raise e


def send_otp_email(user, otp_code: str) -> dict:
    """
    Sends a single-use 6-digit OTP email to the user for 2FA login verification.
    """
    to_email = user.email
    if not to_email:
        logger.warning(f"User {user.username} has no email address configured for OTP delivery.")
        return {"error": "no_email"}

    subject = f"{otp_code} is your Azani Logistics verification code"
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    user_name = user.get_full_name() or user.username

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Azani Logistics Security Verification</title>
      <style>
        body {{
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          background-color: #f8f6f1;
          margin: 0;
          padding: 30px 15px;
          color: #1f2937;
        }}
        .container {{
          max-width: 520px;
          margin: 0 auto;
          background-color: #ffffff;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
          border: 1px solid #e5e7eb;
        }}
        .header {{
          background-color: #111827;
          padding: 24px;
          text-align: center;
          border-bottom: 3px solid #bfa12c;
        }}
        .header h1 {{
          color: #ffffff;
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }}
        .header span {{
          color: #bfa12c;
        }}
        .body-content {{
          padding: 32px 28px;
        }}
        .greeting {{
          font-size: 16px;
          font-weight: 600;
          color: #111827;
          margin-bottom: 12px;
        }}
        .instruction {{
          font-size: 14px;
          line-height: 1.6;
          color: #4b5563;
          margin-bottom: 24px;
        }}
        .otp-box {{
          background-color: #fcfaf5;
          border: 2px dashed #bfa12c;
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          margin: 20px 0 24px 0;
        }}
        .otp-label {{
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: #856f1a;
          font-weight: 700;
          margin-bottom: 6px;
        }}
        .otp-code {{
          font-size: 34px;
          font-weight: 800;
          letter-spacing: 8px;
          color: #111827;
          font-family: 'SF Mono', Monaco, Consolas, monospace;
          margin: 0;
        }}
        .badge {{
          display: inline-block;
          background-color: #fef3c7;
          color: #92400e;
          font-size: 12px;
          font-weight: 600;
          padding: 4px 10px;
          border-radius: 20px;
          margin-top: 10px;
        }}
        .security-notice {{
          background-color: #f3f4f6;
          border-radius: 8px;
          padding: 14px;
          font-size: 12px;
          color: #6b7280;
          line-height: 1.5;
        }}
        .footer {{
          padding: 20px;
          background-color: #f9fafb;
          text-align: center;
          font-size: 12px;
          color: #9ca3af;
          border-top: 1px solid #f3f4f6;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Azani <span>Logistics</span></h1>
        </div>
        <div class="body-content">
          <div class="greeting">Hello {user_name},</div>
          <div class="instruction">
            A sign-in attempt was initiated for your Azani Logistics account. Use the single-use One-Time Password (OTP) below to complete your authentication.
          </div>
          <div class="otp-box">
            <div class="otp-label">Single-Use Verification Code</div>
            <div class="otp-code">{otp_code}</div>
            <div class="badge">Valid for {expiry_minutes} minutes &bull; Single-use only</div>
          </div>
          <div class="security-notice">
            <strong>Security Notice:</strong> If you did not attempt to sign in, please contact your systems administrator immediately. Never share this code with anyone.
          </div>
        </div>
        <div class="footer">
          &copy; Azani Group Limited. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """

    text_content = (
        f"Hello {user_name},\n\n"
        f"Your single-use Azani Logistics verification code is: {otp_code}\n\n"
        f"This code will expire in {expiry_minutes} minutes and can only be used once.\n\n"
        f"If you did not request this code, please contact your administrator immediately."
    )

    return send_resend_email(to_email, subject, html_content, text_content)
