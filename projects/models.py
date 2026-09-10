from decimal import Decimal
import re
from django.db import models
from contractors.models import Subcontractor
from django.contrib.auth.models import User

def extract_short_mda(mda_val):
    if not mda_val:
        return ""
    mda_str = str(mda_val).strip()
    if 'HOUSING AND URBAN DEVELOPMENT' in mda_str.upper():
        return 'FMHUD'
    if 'NIGERIA STORED PRODUCTS RESEARCH' in mda_str.upper():
        return 'NSPRI'
    
    matches = re.findall(r'\(([A-Za-z0-9\s\-]+)\)', mda_str)
    if matches:
        acronyms = [x.strip() for x in matches if len(x.strip()) <= 15 and 'SPECIAL' not in x.upper() and 'MINISTRY' not in x.upper()]
        if acronyms:
            return acronyms[0]
        return matches[0].strip()
    return mda_str

class ProjectCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Category Name")
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Project Category"
        verbose_name_plural = "Project Categories"
        ordering = ['name']

    
    def __str__(self):
        return self.name


class FeeType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Fee Type Name")
    default_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Default Percentage (%)",
        help_text="Default percentage calculated against actual contract amount (e.g. 10.00 for 10%)"
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Fee Type"
        verbose_name_plural = "Fee Types"
        ordering = ['name']

    
    def __str__(self):
        return self.name


class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('CONSTRUCTION', 'Construction / Civil Works'),
        ('SUPPLY_TRAINING', 'Supply and Training Project'),
    ]

    PHASE_CHOICES = [
        ('PRE_AWARD', 'Pre-Award Phase'),
        ('POST_AWARD', 'Post-Award Phase'),
        ('EXECUTION', 'Execution Phase'),
    ]

    # --- Core Identifiers ---
    sn = models.AutoField(primary_key=True, verbose_name="S/N")
    mda = models.CharField(max_length=255, verbose_name="MDA", help_text="Ministry, Department, or Agency")
    project_code = models.CharField(max_length=100, verbose_name="Project Code")
    project_name = models.CharField(max_length=512, verbose_name="Project Name")
    lot = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lot")
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, default='CONSTRUCTION', verbose_name="Type")
    location = models.CharField(max_length=255, verbose_name="Location")
    category = models.ForeignKey(ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Category")
    rolled_over_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rolled_over_to', verbose_name="Rolled Over From")
    parent_project = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='project_parts', verbose_name="Parent Project (for Split Parts)")
    part_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Part Name", help_text="e.g. Phase 1, Phase 2, Part A")
    part_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, verbose_name="Part Percentage", help_text="e.g. 60.00 for 60%")
    
    # --- Documents & Attachments ---
    plain_boq = models.FileField(upload_to='projects/boq/plain/', blank=True, null=True, verbose_name="Plain BOQ")
    priced_boq = models.FileField(upload_to='projects/boq/priced/', blank=True, null=True, verbose_name="Priced BOQ")
    drawing_design = models.FileField(upload_to='projects/drawings/', blank=True, null=True, verbose_name="Drawing/Design")
    award_letter_and_boq = models.FileField(upload_to='projects/boq/awarded/', blank=True, null=True, verbose_name="Award Letter and BOQ")

    # --- Bidding / Pre-Award Phase Tracking ---
    final_companies = models.TextField(blank=True, null=True, verbose_name="Final Companies")
    back_up_companies = models.TextField(blank=True, null=True, verbose_name="Back up Companies")
    updated_recommended_companies = models.TextField(blank=True, null=True, verbose_name="Updated Recommended Companies")
    technical_submission_date = models.DateField(blank=True, null=True, verbose_name="Technical Submission Date")
    financial_submission_date = models.DateField(blank=True, null=True, verbose_name="Financial Submission Date")

    # --- Company Financial Pillars ---
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Budget Amount")
    actual_contract_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Actual Contract Amount")
    
    # --- Internal Benchmarking ---
    in_house_benchmark = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="In-House Benchmark (Direct Labour)")
    cost_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Cost Percentage", help_text="e.g., 65.50 for 65.5%")

    # --- Inflow / Treasury Invoicing ---
    mobilization_received = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Mobilization Received")
    batch_no_mobilization = models.CharField(max_length=100, blank=True, null=True, verbose_name="Batch No. Mobilization")
    batch_no_final_payment = models.CharField(max_length=100, blank=True, null=True, verbose_name="Batch No. Final Payment")
    final_payment_received = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Final Payment Received")

    # --- Management & Status Flags ---
    EXECUTION_MODE_CHOICES = [
        ('SELF_EXECUTED', 'Self-Executed (Direct Labor)'),
        ('SUBCONTRACTED', 'Given to Sub-Contractor'),
    ]
    execution_mode = models.CharField(
        max_length=20,
        choices=EXECUTION_MODE_CHOICES,
        default='SELF_EXECUTED',
        verbose_name="Execution Mode"
    )
    staff_assigned = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Staff Assigned")
    current_phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='PRE_AWARD')
    execution_level_percentage = models.PositiveIntegerField(default=0, verbose_name="Execution Level %")
    project_status = models.CharField(max_length=100, default="Initiated", verbose_name="Project Status")
    payment_status = models.CharField(max_length=100, default="Pending", verbose_name="Payment Status")
    comments = models.TextField(blank=True, null=True, verbose_name="Comments")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    is_supplementary = models.BooleanField(default=False, verbose_name="Is Supplementary Project")

    # --- Intermediary Link for Shared/Split Subcontracting ---
    subcontractors = models.ManyToManyField(
        Subcontractor, 
        through='ProjectAllocation', 
        related_name='assigned_projects'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_parent(self):
        return self.project_parts.exists()

    @property
    def total_budget_amount(self):
        if self.is_parent:
            return sum(part.budget_amount for part in self.project_parts.all())
        return self.budget_amount

    @property
    def total_actual_contract_amount(self):
        if self.is_parent:
            return sum(part.actual_contract_amount for part in self.project_parts.all())
        return self.actual_contract_amount

    @property
    def total_mobilization_received(self):
        if self.is_parent:
            return sum(part.mobilization_received for part in self.project_parts.all())
        return self.mobilization_received

    @property
    def total_final_payment_received(self):
        if self.is_parent:
            return sum(part.final_payment_received for part in self.project_parts.all())
        return self.final_payment_received

    @property
    def average_execution_percentage(self):
        if self.is_parent:
            parts = self.project_parts.all()
            total_parts = parts.count()
            if total_parts > 0:
                total_percentage = sum(part.part_percentage for part in parts)
                if total_percentage > 0:
                    weighted_sum = sum(part.execution_level_percentage * part.part_percentage for part in parts)
                    return int(weighted_sum / total_percentage)
                return int(sum(part.execution_level_percentage for part in parts) / total_parts)
            return 0
        return self.execution_level_percentage

    def save(self, *args, **kwargs):
        if self.mda:
            short = extract_short_mda(self.mda)
            if short:
                self.mda = short
        if self.parent_project:
            self.project_code = self.parent_project.project_code
            self.mda = self.parent_project.mda
            self.location = self.parent_project.location
            self.category = self.parent_project.category

        # Auto-calculate Cost Percentage (In-House Benchmark / Actual Contract Amount or Budget Amount * 100)
        base_amt = self.actual_contract_amount if (self.actual_contract_amount and self.actual_contract_amount > 0) else self.budget_amount
        if base_amt and base_amt > 0 and self.in_house_benchmark:
            self.cost_percentage = round((Decimal(self.in_house_benchmark) / Decimal(base_amt)) * Decimal('100.00'), 2)

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    @property
    def short_mda(self):
        """Return the MDA string stored in the mda column."""
        return self.mda

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project_code} - {self.mda} - {self.project_name}"


    @property
    def total_fees_amount(self):
        """Sum of all fee amounts assigned to the project."""
        if self.is_parent:
            return sum(part.total_fees_amount for part in self.project_parts.all())
        return sum(f.amount for f in self.fees.all())

    @property
    def total_fees_paid(self):
        """Sum of fee amounts marked as PAID."""
        if self.is_parent:
            return sum(part.total_fees_paid for part in self.project_parts.all())
        return sum(f.amount for f in self.fees.filter(status='PAID'))

    @property
    def total_lifecycle_expenses(self):
        """Sum of incurred costs across lifecycle stages."""
        if self.is_parent:
            return sum(part.total_lifecycle_expenses for part in self.project_parts.all())
        return sum(stage.incurred_cost for stage in self.lifecycle_stages.all())

    @property
    def total_unplanned_expenses(self):
        """Sum of unplanned expense outlays."""
        if self.is_parent:
            return sum(part.total_unplanned_expenses for part in self.project_parts.all())
        return sum(exp.amount for exp in self.unplanned_expenses.all())

    @property
    def total_subcontractor_commitments(self):
        """Sum of agreed subcontractor amounts across all allocations."""
        if self.is_parent:
            return sum(part.total_subcontractor_commitments for part in self.project_parts.all())
        return sum(alloc.amount_agreed_with_supplier_contractor for alloc in self.projectallocation_set.all())

    @property
    def total_subcontractor_paid(self):
        """Sum of advances + tranches paid to subcontractors."""
        if self.is_parent:
            return sum(part.total_subcontractor_paid for part in self.project_parts.all())
        return sum(alloc.total_paid for alloc in self.projectallocation_set.all())

    @property
    def total_project_expenses(self):
        """
        Consolidated total project expenses:
        Total Fees + Total Lifecycle Expenses + Total Unplanned Expenses + Total Subcontractor Commitments
        """
        return (
            self.total_fees_amount +
            self.total_lifecycle_expenses +
            self.total_unplanned_expenses +
            self.total_subcontractor_commitments
        )

    @property
    def total_actual_cash_disbursed(self):
        """
        Actual cash paid out to date:
        Fees Paid + Lifecycle Expenses + Unplanned Expenses + Subcontractor Paid
        """
        return (
            self.total_fees_paid +
            self.total_lifecycle_expenses +
            self.total_unplanned_expenses +
            self.total_subcontractor_paid
        )

    @property
    def net_project_margin(self):
        """
        Net projected margin (Contract Amount - Total Expenses).
        """
        return self.total_actual_contract_amount - self.total_project_expenses

    @property
    def net_cashflow_balance(self):
        """
        Net cashflow balance (Total Inflow Received - Actual Cash Disbursed).
        """
        total_inflow = self.total_mobilization_received + self.total_final_payment_received
        return total_inflow - self.total_actual_cash_disbursed

    @property
    def pre_award_phase_comments(self):
        return self.phase_comments.filter(phase='PRE_AWARD')

    @property
    def post_award_phase_comments(self):
        return self.phase_comments.filter(phase='POST_AWARD')

    @property
    def execution_phase_comments(self):
        return self.phase_comments.filter(phase='EXECUTION')

class ProjectFee(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending / Estimated'),
        ('PAID', 'Paid / Disbursed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='fees')
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, verbose_name="Fee Type")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Amount")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING', verbose_name="Status")
    date_paid = models.DateField(blank=True, null=True, verbose_name="Date Paid")
    payment_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Payment Reference",
        help_text="e.g., Bank transfer ref, receipt #"
    )

    class Meta:
        unique_together = ('project', 'fee_type')
        verbose_name = "Project Fee"
        verbose_name_plural = "Project Fees"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project.project_code} - {self.fee_type.name}: ₦{self.amount:,.2f} ({self.get_status_display()})"



class ProjectAllocation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.CASCADE, verbose_name="Sub-Contractor")
    
    # --- Subcontractor Technical Layouts ---
    sub_contractor_drawing_design = models.FileField(upload_to='subcontractors/drawings/', blank=True, null=True, verbose_name="Sub-Contractor Drawing/Design")
    supplier_contractor_price_boq = models.FileField(upload_to='subcontractors/boq/', blank=True, null=True, verbose_name="Supplier/Contractor Price 1/BOQ")
    
    # --- Allocation Financials ---
    sub_contractor_cost_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Sub-Contractor Cost Percentage")
    amount_agreed_with_supplier_contractor = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Amount Agreed with Supplier/Contractor")
    advance_received_by_supplier_contractor = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Advance Received by Supplier/Contractor")
    
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'subcontractor')
        verbose_name = "Project Subcontractor Allocation"
        verbose_name_plural = "Project Subcontractor Allocations"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project.project_code} assigned to {self.subcontractor.name}"

    @property
    def total_paid(self):
        """Calculates total paid (advance plus all tranches)."""
        return self.advance_received_by_supplier_contractor + sum(t.amount for t in self.payment_tranches.all())

    @property
    def remaining_balance(self):
        """Calculates balance remaining for the subcontractor payment schedule."""
        return self.amount_agreed_with_supplier_contractor - self.total_paid


class SubcontractorPaymentTranche(models.Model):
    """
    Tracks installment payments (tranches) made to subcontractors.
    """
    allocation = models.ForeignKey(
        ProjectAllocation, 
        on_delete=models.CASCADE, 
        related_name="payment_tranches"
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name="Amount Paid"
    )
    date_paid = models.DateField(verbose_name="Date Paid")
    payment_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="e.g., Bank transfer Ref, Receipt #"
    )
    notes = models.TextField(
        blank=True, 
        null=True, 
        help_text="Any additional details or remarks."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_paid', '-created_at']
        verbose_name = "Subcontractor Payment Tranche"
        verbose_name_plural = "Subcontractor Payment Tranches"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.allocation.subcontractor.name} - ₦{self.amount:,.2f} on {self.date_paid}"


class ProjectLifecycleStage(models.Model):
    """
    Tracks the completion state and financial footprint of each phase 
    defined in your organizational framework template.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='lifecycle_stages')
    stage_name = models.CharField(max_length=255, help_text="e.g., 'Bi-weekly Purchase of Federal Tender Journal', 'Submission of Batch Numbers to AGF'")
    
    # Order sorting
    sequence_order = models.PositiveIntegerField(help_text="Determines the workflow pipeline order sequence")
    
    # Completion state metrics
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(blank=True, null=True)
    notes_or_updates = models.TextField(blank=True, null=True, help_text="Use this to log internal processing stage and file movement details")
    
    # Framework Rule: 'All stages within the project lifecycle incur costs and should be appropriately captured'
    incurred_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00, 
        help_text="Capture processing costs, profile updates, journal purchase costs, or follow-up expenses here."
    )

    class Meta:
        ordering = ['sequence_order']
        unique_together = ('project', 'stage_name')

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project.project_name} - Step {self.sequence_order}: {self.stage_name} [{'Done' if self.is_completed else 'Pending'}]"


class UnplannedExpense(models.Model):
    """
    Captures ad-hoc or unplanned project costs that do not fall within
    the defined lifecycle pipeline or milestone cash request schedule.
    These are added instantly without any approval workflow.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='unplanned_expenses',
    )
    description = models.CharField(
        max_length=255,
        help_text="Brief description of what the expense was for."
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Total amount of the unplanned expense."
    )
    date_incurred = models.DateField(
        help_text="Date the expense was incurred."
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_expenses',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_incurred']
        verbose_name = "Unplanned Expense"
        verbose_name_plural = "Unplanned Expenses"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project.project_code} — {self.description} (₦{self.amount:,.2f})"


class ProjectMonitoringLog(models.Model):
    """
    Tracks site monitoring visits by engineers.
    They report the physical completion percentage and log any site observations or issues.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="monitoring_logs")
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    start_date = models.DateField(help_text="Start date of the monitoring period/visit")
    end_date = models.DateField(blank=True, null=True, help_text="End date if the monitoring spans multiple days")
    
    description = models.TextField(help_text="Detailed description of current progress, site conditions, or issues.")
    reported_execution_percentage = models.PositiveIntegerField(
        help_text="The engineer's assessment of the overall physical progress (0 to 100)"
    )
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reported_at']
        verbose_name = "Project Monitoring Log"
        verbose_name_plural = "Project Monitoring Logs"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"{self.project.project_code} - {self.reported_execution_percentage}% on {self.start_date}"

    def save(self, *args, **kwargs):
        # Automatically update the parent project's execution percentage
        super().save(*args, **kwargs)
        self.project.execution_level_percentage = self.reported_execution_percentage
        self.project.save(update_fields=['execution_level_percentage'])


class ProjectMonitoringImage(models.Model):
    """
    Allows attaching multiple images/photos to a single site monitoring log.
    """
    monitoring_log = models.ForeignKey(
        ProjectMonitoringLog, 
        on_delete=models.CASCADE, 
        related_name="images"
    )
    image = models.ImageField(upload_to="projects/monitoring_logs/")
    caption = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Optional description of what this image shows (e.g., 'Foundation pouring progress')"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Project Monitoring Image"
        verbose_name_plural = "Project Monitoring Images"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        return f"Image for {self.monitoring_log.project.project_code} log on {self.monitoring_log.start_date}"


class ProjectActivityLog(models.Model):
    """
    Audit log / change notifications for projects.
    Tracks project creation, field modifications, stage updates, financial changes,
    subcontractor allocations, and site monitoring logs.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Project Created'),
        ('UPDATE', 'Project Details Updated'),
        ('FEE', 'Fee Schedule Updated'),
        ('STAGE', 'Lifecycle Stage Progressed'),
        ('EXPENSE', 'Unplanned Expense Logged'),
        ('SUBCONTRACTOR', 'Subcontractor Allocated'),
        ('TRANCHE', 'Payment Tranche Disbursed'),
        ('MONITORING', 'Site Monitoring Logged'),
        ('PHASE_COMMENT', 'Phase Comment Added'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_activity_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, default='UPDATE')
    title = models.CharField(max_length=255, help_text="Short headline summary of the change")
    description = models.TextField(blank=True, null=True, help_text="Detailed summary of updates or observations")
    changes_json = models.JSONField(default=dict, blank=True, help_text="Before & after field value diffs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project Activity Log"
        verbose_name_plural = "Project Activity Logs"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.get_action_type_display()}] {self.project.project_code} by {user_str} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ProjectPhaseComment(models.Model):
    """
    Timestamped staff notes and comments for a specific project phase
    (Pre-Award, Post-Award, or Execution).
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='phase_comments')
    phase = models.CharField(max_length=20, choices=Project.PHASE_CHOICES, verbose_name="Phase")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='phase_comments')
    comment = models.TextField(verbose_name="Comment / Note")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project Phase Comment"
        verbose_name_plural = "Project Phase Comments"

    
    def get_fee_amount(self, fee_type_name):
        """Helper to retrieve amount for a specific FeeType name, falling back to default_percentage calculation if no specific fee record exists or if amount is 0."""
        fee = self.fees.filter(fee_type__name__iexact=fee_type_name).first()
        if fee and fee.amount > 0:
            return fee.amount
        
        fee_type = FeeType.objects.filter(name__iexact=fee_type_name).first()
        if fee_type and fee_type.default_percentage > 0 and self.actual_contract_amount:
            return round((Decimal(self.actual_contract_amount) * Decimal(fee_type.default_percentage)) / Decimal('100.00'), 2)
            
        return Decimal('0.00')

    @property
    def admin_fee_paid(self):
        return self.get_fee_amount('Admin Fee')

    @property
    def facilitation_fee(self):
        return self.get_fee_amount('Facilitation Fee (PR)')

    @property
    def logistics_and_monitoring_fee(self):
        return self.get_fee_amount('Logistics & Monitoring')

    def __str__(self):
        author_str = self.author.username if self.author else "System"
        return f"{self.project.project_code} [{self.get_phase_display()}] note by {author_str} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
