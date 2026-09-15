from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text='Company name')
    director_name = models.CharField(max_length=255, blank=True, default='', help_text='Director name')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return f"{self.name} ({self.director_name})" if self.director_name else self.name

class Subcontractor(models.Model):
    COMPANY_TYPE_CHOICES = [
        ('INTERNAL', 'Internal'),
        ('EXTERNAL', 'External'),
    ]

    name = models.CharField(max_length=255, unique=True, help_text='Name of the subcontractor')
    company_type = models.CharField(max_length=10, choices=COMPANY_TYPE_CHOICES, default='EXTERNAL')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Subcontractor"
        verbose_name_plural = "Subcontractors"

    def __str__(self):
        return f"{self.name} ({self.get_company_type_display()})"


class ComplianceRequirement(models.Model):
    """
    The Master List of required documents. 
    Examples: 'Tax Audit', 'COREN Registration', 'Workmen Compensation Insurance'
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True, help_text="Brief description of what this document entails.")
    is_mandatory = models.BooleanField(default=True, help_text="Is this document strictly required for all contractors?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CompanyCompliance(models.Model):
    """
    The main tracking matrix. Links a Company to a specific requirement, 
    for a specific calendar year.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Missing / Outstanding'),
        ('SUBMITTED', 'Submitted / Under Review'),
        ('APPROVED', 'Approved & Valid'),
        ('EXPIRED', 'Expired / Needs Renewal'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE, 
        related_name='compliance_records'
    )
    requirement = models.ForeignKey(
        ComplianceRequirement, 
        on_delete=models.PROTECT, 
        related_name='subcontractor_records'
    )
    year = models.PositiveIntegerField(
        help_text="The calendar year this compliance record belongs to (e.g., 2026)"
    )
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    
    # Optional document upload field if your superior wants to see the actual document
    uploaded_file = models.FileField(upload_to='compliance_docs/%Y/', blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True, help_text="If the document expires mid-year.")
    
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self):
        """Checks whether the compliance record is past its expiry date or marked EXPIRED."""
        if self.status == 'EXPIRED':
            return True
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def document_filename(self):
        """Returns the base filename of the uploaded document without directory path."""
        if self.uploaded_file and hasattr(self.uploaded_file, 'name'):
            import os
            return os.path.basename(self.uploaded_file.name)
        return ""

    class Meta:
        # Crucial safety constraint: Prevents duplicate tracking entries for the same doc, company, and year.
        unique_together = ('company', 'requirement', 'year')
        indexes = [
            models.Index(fields=['year', 'status']),
            models.Index(fields=['company', 'year']),
        ]
        ordering = ['-year', 'requirement__name']

    def __str__(self):
        return f"{self.company.name} - {self.requirement.name} ({self.year}) - {self.get_status_display()}"