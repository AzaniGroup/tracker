import os
from django import forms
from django.forms.widgets import TextInput, Select

from .models import Company, CompanyCompliance, ComplianceRequirement, Subcontractor


ALLOWED_DOC_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.webp', '.xls', '.xlsx'}
MAX_DOC_SIZE_BYTES = 25 * 1024 * 1024  # 25MB


def validate_document_file(file):
    """Validates file format extension and maximum file size."""
    if file and hasattr(file, 'size'):
        if file.size > MAX_DOC_SIZE_BYTES:
            raise forms.ValidationError("File size exceeds 25MB limit. Please upload a smaller file.")
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            allowed_str = ', '.join(sorted(ALLOWED_DOC_EXTENSIONS))
            raise forms.ValidationError(f"Unsupported file type '{ext}'. Allowed formats: {allowed_str}.")
    return file


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'director_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget = TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'})
        self.fields['director_name'].widget = TextInput(attrs={'class': 'form-control', 'placeholder': 'Director Name'})


class SubcontractorForm(forms.ModelForm):
    class Meta:
        model = Subcontractor
        fields = ['name', 'company_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget = TextInput(attrs={'class': 'form-control', 'placeholder': 'Subcontractor Name'})
        self.fields['company_type'].widget = Select(attrs={'class': 'form-control'})


class ComplianceUpdateForm(forms.ModelForm):
    class Meta:
        model = CompanyCompliance
        fields = ['status', 'expiry_date', 'uploaded_file']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'bg-gray-50 border border-gray-300 rounded text-gray-950 text-xs p-1.5 focus:outline-none focus:ring-1 focus:ring-[#bfa12c] w-full'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-gray-50 border border-gray-300 rounded text-gray-950 text-xs p-1.5 w-full focus:outline-none focus:ring-1 focus:ring-[#bfa12c]'
            }),
            'uploaded_file': forms.FileInput(attrs={
                'class': 'block w-full text-xs text-gray-500 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#bfa12c]'
            }),
        }

    def clean_uploaded_file(self):
        return validate_document_file(self.cleaned_data.get('uploaded_file'))


class SingleComplianceUploadForm(forms.ModelForm):
    class Meta:
        model = CompanyCompliance
        fields = ['status', 'expiry_date', 'uploaded_file']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#bfa12c] focus:border-[#bfa12c] transition duration-150'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'block w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#bfa12c] focus:border-[#bfa12c] transition duration-150'
            }),
            'uploaded_file': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#bfa12c]'
            }),
        }

    def clean_uploaded_file(self):
        return validate_document_file(self.cleaned_data.get('uploaded_file'))


class ComplianceRequirementForm(forms.ModelForm):
    class Meta:
        model = ComplianceRequirement
        fields = ['name', 'description', 'is_mandatory']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#bfa12c] focus:border-[#bfa12c] text-sm text-gray-900 transition duration-150',
                'placeholder': 'Requirement Name (e.g. COREN Audit)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#bfa12c] focus:border-[#bfa12c] text-sm text-gray-900 transition duration-150',
                'rows': 3,
                'placeholder': 'Brief details about document requirements...'
            }),
            'is_mandatory': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-[#bfa12c] focus:ring-[#bfa12c] h-4 w-4 transition duration-150'
            }),
        }