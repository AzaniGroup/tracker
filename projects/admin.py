from django.contrib import admin
from .models import (
    Project, ProjectCategory, FeeType, ProjectFee, UnplannedExpense,
    ProjectMonitoringLog, ProjectMonitoringImage, SubcontractorPaymentTranche,
    ProjectPhaseComment
)

@admin.register(SubcontractorPaymentTranche)
class SubcontractorPaymentTrancheAdmin(admin.ModelAdmin):
    list_display = ('allocation', 'amount', 'date_paid', 'payment_reference', 'created_at')
    list_filter = ('date_paid', 'allocation__project')
    search_fields = ('allocation__subcontractor__name', 'allocation__project__project_code', 'payment_reference')


class ProjectFeeInline(admin.TabularInline):
    model = ProjectFee
    extra = 1

class ProjectMonitoringImageInline(admin.TabularInline):
    model = ProjectMonitoringImage
    extra = 1

class ProjectMonitoringLogInline(admin.TabularInline):
    model = ProjectMonitoringLog
    extra = 0
    fields = ('reported_by', 'start_date', 'end_date', 'reported_execution_percentage', 'description')
    readonly_fields = ('reported_at',)
    show_change_link = True

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'project_code', 'mda', 'project_name', 'project_type', 
        'execution_mode', 'current_phase', 'execution_level_percentage',
        'budget_amount', 'actual_contract_amount'
    )
    list_filter = ('project_type', 'execution_mode', 'current_phase', 'category')
    search_fields = ('project_code', 'project_name', 'mda')
    inlines = [ProjectFeeInline, ProjectMonitoringLogInline]

@admin.register(ProjectMonitoringLog)
class ProjectMonitoringLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'reported_by', 'start_date', 'reported_execution_percentage', 'reported_at')
    list_filter = ('project', 'reported_by', 'start_date')
    search_fields = ('project__project_code', 'project__project_name', 'description')
    inlines = [ProjectMonitoringImageInline]


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_percentage', 'description')
    search_fields = ('name',)

@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_percentage', 'description')
    search_fields = ('name',)

@admin.register(ProjectFee)
class ProjectFeeAdmin(admin.ModelAdmin):
    list_display = ('project', 'fee_type', 'amount')
    list_filter = ('fee_type',)
    search_fields = ('project__project_code', 'project__project_name')


@admin.register(UnplannedExpense)
class UnplannedExpenseAdmin(admin.ModelAdmin):
    list_display = ('project', 'description', 'amount', 'date_incurred', 'reported_by', 'created_at')
    list_filter = ('project', 'date_incurred')
    search_fields = ('description', 'project__project_name', 'project__project_code')
    date_hierarchy = 'date_incurred'
    ordering = ('-date_incurred',)


@admin.register(ProjectPhaseComment)
class ProjectPhaseCommentAdmin(admin.ModelAdmin):
    list_display = ('project', 'phase', 'author', 'created_at')
    list_filter = ('phase', 'project', 'author')
    search_fields = ('comment', 'project__project_code', 'project__project_name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
