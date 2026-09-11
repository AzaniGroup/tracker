import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils import timezone


class JobTitle(models.Model):
    """
    Dynamic table for company designations.
    Allows adding new titles through the UI.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g., Group Managing Director, Civil Engineer, Procurement Specialist",
    )
    permission_group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name='job_titles',
        help_text='Which foundational access level does this title map to?'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Job Title'
        verbose_name_plural = 'Job Titles'

    def __str__(self):
        return f"{self.name} ({self.permission_group.name})"


class Profile(models.Model):
    """
    Extends the base user account to link employees to their dynamic titles.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    job_title = models.ForeignKey(
        JobTitle,
        on_delete=models.PROTECT,
        related_name='employees',
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    last_active_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_2fa_enabled = models.BooleanField(
        default=False, 
        verbose_name="2FA Activated",
        help_text="Designates whether Two-Factor Authentication is activated for this account."
    )

    def __str__(self):
        title = self.job_title.name if self.job_title else 'No Title Assigned'
        return f"{self.user.get_full_name()} - {title}"


class UserOTP(models.Model):
    """
    Stores single-use One-Time Passwords (OTP) for Two-Factor Authentication (2FA).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User OTP'
        verbose_name_plural = 'User OTPs'

    def __str__(self):
        status = "Used" if self.is_used else ("Expired" if self.is_expired else "Active")
        return f"OTP for {self.user.username} ({status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        return (not self.is_used) and (not self.is_expired) and (self.attempts < max_attempts)

    @classmethod
    def generate_otp(cls, user):
        """
        Invalidates any previously issued unused OTPs for the user and generates a fresh,
        single-use 6-digit numeric OTP valid for OTP_EXPIRY_MINUTES.
        """
        # Invalidate existing unused codes
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate a secure 6-digit code
        code = f"{secrets.randbelow(900000) + 100000}"
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        otp = cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at,
            is_used=False,
            attempts=0
        )
        return otp

    @classmethod
    def verify_code(cls, user, candidate_code):
        """
        Verifies a candidate OTP for a user.
        Strict single-use: marks as used immediately on successful verification.
        Returns: (success: bool, status_message: str)
        """
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        candidate_code = str(candidate_code).strip()

        # Fetch latest unused OTP for user
        otp = cls.objects.filter(user=user, is_used=False).order_by('-created_at').first()

        if not otp:
            return False, "No active verification code found. Please request a new code."

        if otp.is_expired:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            return False, "Verification code has expired. Please request a new code."

        if otp.attempts >= max_attempts:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            return False, "Maximum verification attempts exceeded. Please request a new code."

        if otp.code == candidate_code:
            # Mark single-use code as consumed immediately
            otp.is_used = True
            otp.used_at = timezone.now()
            otp.save(update_fields=['is_used', 'used_at'])
            return True, "Verification successful."
        else:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            remaining = max_attempts - otp.attempts
            if remaining <= 0:
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                return False, "Maximum verification attempts reached. Please request a new code."
            return False, f"Invalid verification code. {remaining} attempt(s) remaining."

