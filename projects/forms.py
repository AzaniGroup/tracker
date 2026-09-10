from django import forms
from django.forms import inlineformset_factory
from .models import (
    Project, ProjectCategory, ProjectAllocation, ProjectLifecycleStage, 
    ProjectFee, FeeType, ProjectMonitoringLog, ProjectMonitoringImage,
    SubcontractorPaymentTranche, ProjectPhaseComment
)

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'project_code', 'mda', 'project_name', 'project_type', 'execution_mode', 'lot', 'location', 'category', 
            'rolled_over_from', 'parent_project', 'part_name', 'part_percentage',
            'budget_amount', 'technical_submission_date', 'financial_submission_date', 'final_companies', 'back_up_companies', 'updated_recommended_companies',
            'plain_boq', 'priced_boq', 'drawing_design',
            'actual_contract_amount', 'in_house_benchmark', 'cost_percentage', 'staff_assigned', 'current_phase',
            'mobilization_received', 'batch_no_mobilization', 'final_payment_received', 'batch_no_final_payment',
            'award_letter_and_boq',
            'execution_level_percentage', 'project_status', 'payment_status', 'comments', 'remarks'
        ]
        widgets = {
            'technical_submission_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'financial_submission_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'plain_boq': forms.FileInput(attrs={'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded-md shadow-sm'}),
            'priced_boq': forms.FileInput(attrs={'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded-md shadow-sm'}),
            'drawing_design': forms.FileInput(attrs={'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded-md shadow-sm'}),
            'award_letter_and_boq': forms.FileInput(attrs={'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded-md shadow-sm'}),
            'comments': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'final_companies': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'back_up_companies': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'updated_recommended_companies': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['rolled_over_from'].queryset = Project.objects.exclude(pk=self.instance.pk)
            self.fields['parent_project'].queryset = Project.objects.exclude(pk=self.instance.pk)
        
        # Style form fields using modern Tailwind classes
        for name, field in self.fields.items():
            if name not in ['comments', 'remarks', 'final_companies', 'back_up_companies', 'updated_recommended_companies']:
                field.widget.attrs.setdefault('class', 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm')


ProjectFeeFormSet = inlineformset_factory(
    Project,
    ProjectFee,
    fields=('fee_type', 'amount', 'status', 'date_paid', 'payment_reference'),
    extra=1,
    can_delete=True,
    widgets={
        'fee_type': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        'amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        'status': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        'date_paid': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        'payment_reference': forms.TextInput(attrs={'placeholder': 'e.g., Transfer ID / Receipt #', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
    }
)

class ProjectAllocationForm(forms.ModelForm):
    class Meta:
        model = ProjectAllocation
        fields = [
            'subcontractor', 'sub_contractor_drawing_design', 'supplier_contractor_price_boq',
            'sub_contractor_cost_percentage', 'amount_agreed_with_supplier_contractor',
            'advance_received_by_supplier_contractor'
        ]

class ProjectLifecycleStageForm(forms.ModelForm):
    class Meta:
        model = ProjectLifecycleStage
        fields = ['is_completed', 'completed_date', 'notes_or_updates', 'incurred_cost']
        widgets = {
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
            'notes_or_updates': forms.Textarea(attrs={'rows': 2}),
        }


class ProjectCategoryForm(forms.ModelForm):
    class Meta:
        model = ProjectCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        }


class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'default_percentage', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'default_percentage': forms.NumberInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm', 'step': '0.01', 'placeholder': 'e.g. 10.00 for 10%'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
        }


class ProjectMonitoringLogForm(forms.ModelForm):
    class Meta:
        model = ProjectMonitoringLog
        fields = ['start_date', 'end_date', 'reported_execution_percentage', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'reported_execution_percentage': forms.NumberInput(attrs={'min': 0, 'max': 100, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm', 'placeholder': 'Provide a detailed description of what is happening on site...'}),
        }


class ProjectMonitoringLogGlobalForm(ProjectMonitoringLogForm):
    class Meta(ProjectMonitoringLogForm.Meta):
        fields = ['project'] + ProjectMonitoringLogForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].widget.attrs.update({'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'})
        self.fields['project'].queryset = Project.objects.all()
class SubcontractorPaymentTrancheForm(forms.ModelForm):
    class Meta:
        model = SubcontractorPaymentTranche
        fields = ['amount', 'date_paid', 'payment_reference', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'date_paid': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm'}),
            'payment_reference': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm', 'placeholder': 'e.g., Transfer ID, bank transaction code'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm', 'placeholder': 'Any supporting description...'}),
        }


class ProjectPhaseCommentForm(forms.ModelForm):
    class Meta:
        model = ProjectPhaseComment
        fields = ['phase', 'comment']
        widgets = {
            'phase': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-1.5 px-2.5 text-xs font-semibold'}),
            'comment': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#bfa12c] focus:ring-[#bfa12c] py-2 px-3 text-sm', 'placeholder': 'Enter comment or update note for this phase...'}),
        }


