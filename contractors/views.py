from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView, View
from urllib.parse import urlencode

from .forms import CompanyForm, ComplianceRequirementForm, ComplianceUpdateForm, SubcontractorForm
from .models import Company, CompanyCompliance, ComplianceRequirement, Subcontractor


from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import Http404

class CompanyListView(ListView):
    model = Company
    template_name = 'contractors/list_company.html'
    context_object_name = 'companies'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(Q(name__icontains=search_query) | Q(director_name__icontains=search_query))
        return queryset

    def paginate_queryset(self, queryset, page_size):
        try:
            return super().paginate_queryset(queryset, page_size)
        except (EmptyPage, InvalidPage, Http404):
            paginator = self.get_paginator(
                queryset, page_size, orphans=self.get_paginate_orphans(),
                allow_empty_first_page=self.get_allow_empty()
            )
            page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)
            return (paginator, page_obj, page_obj.object_list, page_obj.has_other_pages())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Companies'
        context['current_search'] = self.request.GET.get('q', '')
        return context

class SubcontractorListView(ListView):
    model = Subcontractor
    template_name = 'contractors/list_contractor.html'
    context_object_name = 'subcontractors'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        type_filter = self.request.GET.get('type', '').strip().upper()
        if type_filter in ['INTERNAL', 'EXTERNAL']:
            queryset = queryset.filter(company_type=type_filter)
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

    def paginate_queryset(self, queryset, page_size):
        try:
            return super().paginate_queryset(queryset, page_size)
        except (EmptyPage, InvalidPage, Http404):
            paginator = self.get_paginator(
                queryset, page_size, orphans=self.get_paginate_orphans(),
                allow_empty=self.get_allow_empty()
            )
            page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)
            return (paginator, page_obj, page_obj.object_list, page_obj.has_other_pages())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Subcontractors'
        context['current_search'] = self.request.GET.get('q', '')
        context['current_type'] = self.request.GET.get('type', '')
        return context


def add_subcontractor(request):
    if not (request.user.is_authenticated and (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    )):
        messages.error(request, "You do not have permission to add subcontractors.")
        return redirect('contractors:contractor_list')
    if request.method == 'POST':
        form = SubcontractorForm(request.POST)  
        if form.is_valid():
            form.save()
            messages.success(request, f"Subcontractor '{form.cleaned_data['name']}' added successfully.")
        else:
            messages.error(request, form.errors)
        return redirect('contractors:contractor_list')
    form = SubcontractorForm()
    return render(request, 'contractors/add_subcontractor.html', 
                        {'page_title': 'Add Subcontractor', 
                        'form':form })

def edit_subcontractor(request, pk):
    if not (request.user.is_authenticated and (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    )):
        messages.error(request, "You do not have permission to edit subcontractors.")
        return redirect('contractors:contractor_list')
    sub = get_object_or_404(Subcontractor, pk=pk)
    if request.method == 'POST':
        form = SubcontractorForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subcontractor '{sub.name}' updated successfully.")
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('contractors:contractor_list')
    else:
        form = SubcontractorForm(instance=sub)

    context = {
        'page_title': 'Edit Contractor',
        'subcontractor': sub,
        'form': form,
    }
    return render(request, 'contractors/edit_subcontractor.html', context)


def add_company(request):
    if not (request.user.is_authenticated and (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    )):
        messages.error(request, "You do not have permission to add companies.")
        return redirect('contractors:company_list')
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company '{form.cleaned_data['name']}' added successfully.")
            return redirect('contractors:company_list')
    else:
        form = CompanyForm()
    return render(request, 'contractors/add_company.html', {'page_title': 'Add Company', 'form': form})


def edit_company(request, pk):
    if not (request.user.is_authenticated and (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    )):
        messages.error(request, "You do not have permission to edit companies.")
        return redirect('contractors:company_list')
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company '{company.name}' updated successfully.")
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('contractors:company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'contractors/edit_company.html', {'page_title': 'Edit Company', 'company': company, 'form': form})


@login_required
@require_POST
def delete_company(request, pk):
    if not (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    ):
        messages.error(request, "You do not have permission to delete companies.")
        return redirect('contractors:company_list')
    company = get_object_or_404(Company, pk=pk)
    company.delete()
    messages.success(request, f"Company '{company.name}' deleted successfully.")
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('contractors:company_list')


@login_required
@require_POST
def delete_subcontractor(request, pk):
    if not (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    ):
        messages.error(request, "You do not have permission to delete subcontractors.")
        return redirect('contractors:contractor_list')
    sub = get_object_or_404(Subcontractor, pk=pk)
    sub.delete()  
    messages.success(request, f"Subcontractor '{sub.name}' deleted successfully.")  
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('contractors:contractor_list')  


class ComplianceMatrixView(TemplateView):
    template_name = 'contractors/compliance_matrix.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Get the target year from the URL query parameters, default to current year
        current_year = timezone.now().year
        selected_year = int(self.request.GET.get('year', current_year))
        
        # 2. Fetch all active requirements and companies
        requirements = ComplianceRequirement.objects.all()
        companies = Company.objects.all()
        
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            companies = companies.filter(Q(name__icontains=search_query) | Q(contact__icontains=search_query))
        
        # 3. Pull all compliance records for the target year in ONE optimized database hit
        compliance_records = CompanyCompliance.objects.filter(year=selected_year).select_related(
            'company', 'requirement'
        )
        
        # 4. Build a lookup dictionary: {(company_id, requirement_id): record_status_or_object}
        # This acts as our fast-access database cache in memory
        lookup_matrix = {
            (record.company_id, record.requirement_id): record 
            for record in compliance_records
        }
        
        # 5. Restructure the data into a clean grid dictionary for easy template looping
        matrix_data = []
        for company in companies:
            company_row = {
                'company': company,
                'requirements': [],
                'fully_compliant': True  # Assume true until proven otherwise
            }
            
            for req in requirements:
                record = lookup_matrix.get((company.id, req.id))
                
                # Evaluate compliance status for the row
                status = record.status if record else 'PENDING'
                is_valid = status in ['APPROVED', 'SUBMITTED']
                
                if req.is_mandatory and not is_valid:
                    company_row['fully_compliant'] = False
                
                company_row['requirements'].append({
                    'requirement': req,
                    'record': record,
                    'status': status
                })
                
            matrix_data.append(company_row)
            
        # 6. Populate Context variables for the HTML template
        context['page_title'] = f'Annual Company Compliance Matrix ({selected_year})'
        context['selected_year'] = selected_year
        # Generate a list of years for a year-picker dropdown menu (e.g., past 3 years to next year)
        context['year_range'] = range(current_year - 3, current_year + 2)
        context['requirements'] = requirements
        context['matrix_data'] = matrix_data
        context['current_search'] = search_query
        
        return context

class ManageComplianceView(View):
    template_name = 'contractors/manage_compliance.html'
    paginate_by = 10

    def get_context_for_request(self, request, formset=None):
        current_year = timezone.now().year
        try:
            selected_year = int(request.GET.get('year', current_year))
        except (ValueError, TypeError):
            selected_year = current_year

        search_query = request.GET.get('q', '').strip()
        page_number = request.GET.get('page', 1)

        companies_qs = Company.objects.all().order_by('name')
        if search_query:
            companies_qs = companies_qs.filter(
                Q(name__icontains=search_query) | Q(director_name__icontains=search_query)
            )

        paginator = Paginator(companies_qs, self.paginate_by)
        try:
            page_obj = paginator.page(page_number)
        except (EmptyPage, InvalidPage):
            page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

        companies = page_obj.object_list
        requirements = list(ComplianceRequirement.objects.all().order_by('name'))

        # Auto-provision missing rows for current page's companies safely in bulk
        existing_pairs = set(
            CompanyCompliance.objects.filter(
                year=selected_year,
                company__in=companies
            ).values_list('company_id', 'requirement_id')
        )
        to_create = []
        for company in companies:
            for req in requirements:
                if (company.id, req.id) not in existing_pairs:
                    to_create.append(
                        CompanyCompliance(
                            company=company,
                            requirement=req,
                            year=selected_year,
                            status='PENDING'
                        )
                    )
        if to_create:
            CompanyCompliance.objects.bulk_create(to_create, ignore_conflicts=True)

        queryset = CompanyCompliance.objects.filter(
            year=selected_year,
            company__in=companies
        ).select_related('company', 'requirement').order_by('company__name', 'requirement__name')

        ComplianceFormSet = modelformset_factory(CompanyCompliance, form=ComplianceUpdateForm, extra=0)

        if formset is None:
            formset = ComplianceFormSet(queryset=queryset)

        # Map forms by (company_id, requirement_id)
        form_map = {
            (form.instance.company_id, form.instance.requirement_id): form
            for form in formset
        }

        company_rows = []
        for company in companies:
            row_items = []
            for req in requirements:
                form = form_map.get((company.id, req.id))
                row_items.append({
                    'form': form,
                    'requirement': req,
                })
            company_rows.append({
                'company': company,
                'row_items': row_items,
            })

        # Query string for pagination links preserving year & q
        query_params = request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        query_string = query_params.urlencode()

        context = {
            'page_title': f'Manage Annual Company Compliance ({selected_year})',
            'formset': formset,
            'company_rows': company_rows,
            'selected_year': selected_year,
            'year_range': range(current_year - 2, current_year + 2),
            'requirements': requirements,
            'paginator': paginator,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'current_search': search_query,
            'query_string': query_string,
            'total_companies_count': companies_qs.count(),
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_for_request(request)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        current_year = timezone.now().year
        try:
            selected_year = int(request.GET.get('year', current_year))
        except (ValueError, TypeError):
            selected_year = current_year

        search_query = request.GET.get('q', '').strip()
        page_number = request.GET.get('page', '1')

        ComplianceFormSet = modelformset_factory(CompanyCompliance, form=ComplianceUpdateForm, extra=0)
        formset = ComplianceFormSet(request.POST)

        if formset.is_valid():
            formset.save()
            messages.success(request, "Compliance records updated successfully.")
            params = {}
            if selected_year:
                params['year'] = selected_year
            if search_query:
                params['q'] = search_query
            if page_number and page_number != '1':
                params['page'] = page_number
            redirect_url = reverse('contractors:manage_compliance')
            if params:
                redirect_url += f"?{urlencode(params)}"
            return redirect(redirect_url)

        # If errors happen, reload screen with state
        messages.error(request, "Please correct the errors in the form before submitting.")
        context = self.get_context_for_request(request, formset=formset)
        return render(request, self.template_name, context)

@login_required
def manage_compliance_requirements(request):
    if not (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Level 3', 'Level 4']).exists()
    ):
        messages.error(request, "Permission denied. You do not have authorization to manage compliance requirements.")
        return redirect('contractors:compliance_matrix')

    edit_id = request.GET.get('edit')
    req_instance = None
    if edit_id:
        req_instance = get_object_or_404(ComplianceRequirement, pk=edit_id)
        
    if request.method == 'POST':
        form = ComplianceRequirementForm(request.POST, instance=req_instance)
        if form.is_valid():
            form.save()
            if req_instance:
                messages.success(request, "Compliance requirement updated successfully.")
            else:
                messages.success(request, "New compliance requirement added successfully.")
            return redirect('contractors:manage_compliance_requirements')
    else:
        form = ComplianceRequirementForm(instance=req_instance)
    
    requirements = ComplianceRequirement.objects.all()
    context = {
        'page_title': 'Manage Company Compliance Requirements',
        'requirements': requirements,
        'form': form,
        'is_editing': req_instance is not None,
        'edit_instance': req_instance,
    }
    return render(request, 'contractors/manage_requirements.html', context)