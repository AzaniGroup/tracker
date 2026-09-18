import logging
import resend
from django.conf import settings
from django.utils.html import escape, linebreaks

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
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Azani Project Tracker <onboarding@resend.dev>')

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

    subject = f"{otp_code} is your Azani Project Tracker verification code"
    expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
    user_name = escape(user.get_full_name() or user.username)
    safe_otp = escape(str(otp_code))

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Azani Project Tracker Security Verification</title>
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
          <h1>Azani <span>Project Tracker</span></h1>
        </div>
        <div class="body-content">
          <div class="greeting">Hello {user_name},</div>
          <div class="instruction">
            A sign-in attempt was initiated for your Azani Project Tracker account. Use the single-use One-Time Password (OTP) below to complete your authentication.
          </div>
          <div class="otp-box">
            <div class="otp-label">Single-Use Verification Code</div>
            <div class="otp-code">{safe_otp}</div>
            <div class="badge">Valid for {expiry_minutes} minutes &bull; Single-use only</div>
          </div>
          <div class="security-notice">
            <strong>Security Notice:</strong> If you did not attempt to sign in, please contact your systems administrator immediately. Never share this code with anyone.
          </div>
        </div>
        <div class="footer">
          &copy; Azani Project Tracker &bull; Azani Group. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """

    plain_user_name = user.get_full_name() or user.username
    text_content = (
        f"Hello {plain_user_name},\n\n"
        f"Your single-use Azani Project Tracker verification code is: {otp_code}\n\n"
        f"This code will expire in {expiry_minutes} minutes and can only be used once.\n\n"
        f"If you did not request this code, please contact your administrator immediately."
    )

    return send_resend_email(to_email, subject, html_content, text_content)


def send_progress_log_notification(monitoring_log) -> list:
    """
    Sends an email update to all Level 4 staff and superusers when a new progress/monitoring log is created.
    """
    from django.contrib.auth.models import User
    from django.db.models import Q

    # Fetch active Level 4 staff and superusers who have an email address configured
    recipients = list(
        User.objects.filter(
            Q(groups__name='Level 4') | Q(is_superuser=True),
            is_active=True
        ).exclude(email='').values_list('email', flat=True).distinct()
    )

    if not recipients:
        logger.info("No Level 4 recipients found to send progress log email notification.")
        return []

    project = monitoring_log.project
    raw_reporter = monitoring_log.reported_by.get_full_name() or monitoring_log.reported_by.username
    reporter_name = escape(raw_reporter)
    project_code = escape(project.project_code)
    project_name = escape(project.project_name)
    mda_text = escape(project.mda or 'N/A')
    location_text = escape(project.location or 'N/A')
    progress_pct = monitoring_log.reported_execution_percentage
    date_str = escape(monitoring_log.start_date.strftime("%b %d, %Y") if monitoring_log.start_date else "Recent")
    if monitoring_log.end_date and monitoring_log.end_date != monitoring_log.start_date:
        date_str += f" – {escape(monitoring_log.end_date.strftime('%b %d, %Y'))}"
    
    images_count = monitoring_log.images.count()
    images_text = f"{images_count} site photo(s) attached" if images_count > 0 else "No photos attached"
    escaped_notes = linebreaks(escape(monitoring_log.description or 'No notes provided.'))

    subject = f"[Progress Update {progress_pct}%] {project.project_code} - {project.project_name[:50]}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Site Progress Update</title>
      <style>
        body {{
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          background-color: #f8f6f1;
          margin: 0;
          padding: 30px 15px;
          color: #1f2937;
        }}
        .container {{
          max-width: 580px;
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
          padding: 28px 24px;
        }}
        .badge-progress {{
          display: inline-block;
          background-color: #ecfdf5;
          border: 1px solid #a7f3d0;
          color: #065f46;
          font-size: 13px;
          font-weight: 700;
          padding: 6px 14px;
          border-radius: 20px;
          margin-bottom: 16px;
        }}
        .project-title {{
          font-size: 18px;
          font-weight: 700;
          color: #111827;
          margin-bottom: 6px;
          line-height: 1.4;
        }}
        .project-meta {{
          font-size: 13px;
          color: #6b7280;
          margin-bottom: 20px;
        }}
        .info-card {{
          background-color: #f9fafb;
          border-radius: 10px;
          padding: 16px;
          border: 1px solid #e5e7eb;
          margin-bottom: 20px;
        }}
        .info-table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }}
        .info-table td {{
          padding: 6px 0;
          border-bottom: 1px solid #f3f4f6;
        }}
        .info-table tr:last-child td {{
          border-bottom: none;
        }}
        .info-label {{
          font-weight: 600;
          color: #4b5563;
          width: 40%;
        }}
        .info-value {{
          color: #111827;
          text-align: right;
        }}
        .notes-box {{
          background-color: #fffdf5;
          border-left: 4px solid #bfa12c;
          padding: 14px 16px;
          border-radius: 4px;
          margin-top: 10px;
          font-size: 13px;
          line-height: 1.6;
          color: #374151;
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
          <h1>Azani <span>Project Tracker</span></h1>
        </div>
        <div class="body-content">
          <div class="badge-progress">
            Site Progress: {progress_pct}% Overall Completion
          </div>
          <div class="project-title">
            {project_code} &mdash; {project_name}
          </div>
          <div class="project-meta">
            MDA: {mda_text} &bull; Location: {location_text}
          </div>

          <div class="info-card">
            <table class="info-table">
              <tr>
                <td class="info-label">Reported By</td>
                <td class="info-value">{reporter_name}</td>
              </tr>
              <tr>
                <td class="info-label">Monitoring Date</td>
                <td class="info-value">{date_str}</td>
              </tr>
              <tr>
                <td class="info-label">Reported Execution</td>
                <td class="info-value"><strong>{progress_pct}%</strong></td>
              </tr>
              <tr>
                <td class="info-label">Site Documentation</td>
                <td class="info-value">{images_text}</td>
              </tr>
            </table>
          </div>

          <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin-top: 20px;">
            Engineer Site Notes & Observations
          </div>
          <div class="notes-box">
            {escaped_notes}
          </div>
        </div>
        <div class="footer">
          &copy; Azani Project Tracker &bull; Azani Group. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """

    text_content = (
        f"Site Progress Update - {project.project_code} ({progress_pct}%)\n\n"
        f"Project: {project.project_name}\n"
        f"MDA: {project.mda or 'N/A'}\n"
        f"Location: {project.location or 'N/A'}\n"
        f"Reported By: {raw_reporter}\n"
        f"Date: {monitoring_log.start_date.strftime('%b %d, %Y') if monitoring_log.start_date else 'Recent'}\n"
        f"Progress: {progress_pct}%\n"
        f"Documentation: {images_text}\n\n"
        f"Site Notes:\n{monitoring_log.description or 'No notes provided.'}\n\n"
        f"---\nAzani Project Tracker"
    )

    responses = []
    for email in recipients:
        try:
            resp = send_resend_email(email, subject, html_content, text_content)
            responses.append(resp)
        except Exception as e:
            logger.error(f"Failed sending progress log notification to {email}: {e}")

    return responses


def send_2fa_enabled_confirmation_email(user) -> dict:
    """
    Sends a confirmation email to the user notifying them that Two-Factor Authentication (OTP)
    has been successfully activated for their account at their confirmed email address.
    """
    to_email = user.email
    if not to_email:
        logger.warning(f"User {user.username} has no email address to receive 2FA activation confirmation.")
        return {"error": "no_email"}

    subject = "Two-Factor Authentication (OTP) Activated - Azani Project Tracker"
    user_name = escape(user.get_full_name() or user.username)
    safe_email = escape(to_email)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>2FA Security Activated - Azani Project Tracker</title>
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
          margin-bottom: 20px;
        }}
        .status-box {{
          background-color: #ecfdf5;
          border: 1px solid #a7f3d0;
          border-radius: 12px;
          padding: 18px 20px;
          margin: 20px 0 24px 0;
        }}
        .status-title {{
          font-size: 14px;
          color: #065f46;
          font-weight: 700;
          margin-bottom: 4px;
        }}
        .status-desc {{
          font-size: 13px;
          color: #047857;
          line-height: 1.5;
        }}
        .security-notice {{
          background-color: #fffbeb;
          border-left: 3px solid #f59e0b;
          padding: 12px 16px;
          font-size: 12px;
          color: #92400e;
          border-radius: 4px;
          margin-top: 20px;
        }}
        .footer {{
          background-color: #f9fafb;
          padding: 18px 24px;
          text-align: center;
          font-size: 11px;
          color: #9ca3af;
          border-top: 1px solid #f3f4f6;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Azani <span>Project Tracker</span></h1>
        </div>
        <div class="body-content">
          <div class="greeting">Hello {user_name},</div>
          <div class="instruction">
            Two-Factor Authentication (OTP) has been successfully activated for your account.
          </div>
          <div class="status-box">
            <div class="status-title">&check; Confirmed Delivery Email</div>
            <div class="status-desc">
              Single-use 6-digit login verification codes will be sent to: <strong>{safe_email}</strong>.
            </div>
          </div>
          <div class="instruction">
            Whenever you log into your Azani Project Tracker account, a verification code will be dispatched to this address to verify your identity.
          </div>
          <div class="security-notice">
            <strong>Security Notice:</strong> If you did not perform or authorize this action, please contact your Azani systems administrator immediately to protect your account.
          </div>
        </div>
        <div class="footer">
          &copy; Azani Project Tracker &bull; Azani Group. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """

    plain_user_name = user.get_full_name() or user.username
    text_content = (
        f"Hello {plain_user_name},\n\n"
        f"Two-Factor Authentication (OTP) has been successfully activated for your Azani Project Tracker account.\n\n"
        f"Confirmed Delivery Email: {to_email}\n"
        f"Single-use verification codes will now be sent to this email address on every sign-in attempt.\n\n"
        f"If you did not activate this security feature, please contact your administrator immediately.\n\n"
        f"---\nAzani Project Tracker"
    )

    try:
        return send_resend_email(to_email, subject, html_content, text_content)
    except Exception as e:
        logger.error(f"Failed sending 2FA activation confirmation email to {to_email}: {e}")
        return {"error": str(e)}

