import openpyxl
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.contrib import messages     
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as BaseLoginView
from django.db.models import Sum, F, Q
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)

from projects.models import ProjectLifecycleStage, Project, UnplannedExpense
from logistic.models import MilestoneCashRequest
from users.models import UserOTP
from core.services.email_service import send_otp_email

User = get_user_model()


def mask_email(email: str) -> str:
    """Masks an email address for privacy (e.g. dama@azanigroup.com.ng -> d***@azanigroup.com.ng)."""
    if not email or '@' not in email:
        return email or ''
    user_part, domain_part = email.split('@', 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + '***'
    else:
        masked_user = user_part[0] + '*' * (len(user_part) - 2) + user_part[-1]
    return f"{masked_user}@{domain_part}"


class CustomLoginView(BaseLoginView):
    """
    Handles user login. If user has 2FA enabled:
    - Sets pre-2FA session state.
    - Generates a single-use 6-digit OTP and emails it via Resend.
    - Redirects user to OTP verification screen.
    If 2FA is disabled, logs in immediately.
    """
    template_name = 'registration/login.html'

    def form_valid(self, form):
        user = form.get_user()
        remember_me = self.request.POST.get('remember-me') == 'on'

        profile = getattr(user, 'profile', None)
        if profile and profile.is_2fa_enabled and user.email:
            # Setup session for OTP step
            self.request.session['pre_2fa_user_id'] = user.pk
            self.request.session['pre_2fa_remember_me'] = remember_me
            self.request.session['pre_2fa_next'] = self.get_redirect_url() or ''

            # Generate single-use OTP (invalidating previous ones)
            otp = UserOTP.generate_otp(user)

            # Send OTP email
            try:
                send_otp_email(user, otp.code)
            except Exception:
                pass

            messages.info(
                self.request,
                f"Two-Factor Authentication is active. A single-use verification code has been sent to {mask_email(user.email)}."
            )
            return redirect('core:verify_otp')

        # Standard login
        auth_login(self.request, user)
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)

        return redirect(self.get_success_url())


class VerifyOTPView(View):
    """
    Verifies single-use OTP codes for 2FA login.
    """
    template_name = 'registration/verify_otp.html'

    def get(self, request):
        user_id = request.session.get('pre_2fa_user_id')
        if not user_id:
            return redirect('core:login')

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            request.session.pop('pre_2fa_user_id', None)
            return redirect('core:login')

        context = {
            'masked_email': mask_email(user.email),
            'user': user,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        user_id = request.session.get('pre_2fa_user_id')
        if not user_id:
            messages.error(request, "Session expired. Please sign in again.")
            return redirect('core:login')

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            request.session.pop('pre_2fa_user_id', None)
            return redirect('core:login')

        otp_code = request.POST.get('otp_code', '').strip()
        if not otp_code:
            messages.error(request, "Please enter your 6-digit verification code.")
            return render(request, self.template_name, {'masked_email': mask_email(user.email), 'user': user})

        success, status_msg = UserOTP.verify_code(user, otp_code)
        if success:
            # Log the user in
            auth_login(request, user)
            remember_me = request.session.pop('pre_2fa_remember_me', False)
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)

            next_url = request.session.pop('pre_2fa_next', '')
            request.session.pop('pre_2fa_user_id', None)

            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            if next_url:
                return redirect(next_url)
            return redirect(settings.LOGIN_REDIRECT_URL)

        messages.error(request, status_msg)
        return render(request, self.template_name, {'masked_email': mask_email(user.email), 'user': user})


class ResendOTPView(View):
    """
    Generates a new single-use OTP and sends an email via Resend.
    """
    def post(self, request):
        user_id = request.session.get('pre_2fa_user_id')
        if not user_id:
            messages.error(request, "Session expired. Please sign in again.")
            return redirect('core:login')

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            request.session.pop('pre_2fa_user_id', None)
            return redirect('core:login')

        if not user.email:
            messages.error(request, "No registered email address found for your account.")
            return redirect('core:verify_otp')

        # Invalidate old OTPs and generate fresh code
        otp = UserOTP.generate_otp(user)
        try:
            send_otp_email(user, otp.code)
            messages.success(request, f"A new verification code was sent to {mask_email(user.email)}.")
        except Exception:
            messages.error(request, "Could not send email at this time. Please try again.")

        return redirect('core:verify_otp')


def logout_view(request):
    """Log out the user and redirect to login page.
    Accepts GET requests to avoid 405 errors.
    """
    auth_logout(request)
    return redirect('core:login')




class ProjectRequiredMixin(LoginRequiredMixin):
    """Mixin to filter querysets by the project selected in the session.
    All views that inherit this mixin will have a ``self.project`` attribute
    representing the currently active project (or ``None`` if not selected).
    """

    def dispatch(self, request, *args, **kwargs):
        project_id = request.GET.get("project")
        self.project = None
        if project_id and project_id != '0':
            self.project = get_object_or_404(Project, pk=project_id)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "project", None):
            # Assume the model has a ``project`` FK; filter accordingly.
            if "project" in [f.name for f in qs.model._meta.get_fields()]:
                qs = qs.filter(project=self.project)
        return qs


class ProjectSwitcherView(LoginRequiredMixin, View):
    """Simple view that stores the chosen project ID in the session.
    URL pattern: ``project/<int:pk>/select/``.
    After switching, redirects back to the page that requested the switch
    (using ``HTTP_REFERER``) or to the dashboard as a fallback.
    """

    def get(self, request, pk):
        from urllib.parse import urlparse
        from django.urls import resolve, reverse, Resolver404

        if pk == 0:
            if "project_id" in request.session:
                del request.session["project_id"]
            if "project_name" in request.session:
                del request.session["project_name"]
        else:
            # Validate the project exists.
            project = get_object_or_404(Project, pk=pk)
            request.session["project_id"] = project.sn
            request.session["project_name"] = project.project_code

        # Redirect back.
        next_url = request.META.get("HTTP_REFERER") or reverse("core:dashboard")
        
        if request.META.get("HTTP_REFERER"):
            parsed = urlparse(next_url)
            try:
                match = resolve(parsed.path)
                if 'project_id' in match.kwargs:
                    if pk == 0:
                        # Cannot stay on a project-specific page if "ALL" is selected
                        next_url = reverse("core:dashboard")
                    else:
                        match.kwargs['project_id'] = pk
                        next_url = reverse(match.view_name, args=match.args, kwargs=match.kwargs)
                elif 'pk' in match.kwargs and match.view_name.startswith('projects:'):
                    # For project detail pages, 'pk' might be the project id
                    if pk == 0:
                        next_url = reverse("core:dashboard")
                    else:
                        match.kwargs['pk'] = pk
                        next_url = reverse(match.view_name, args=match.args, kwargs=match.kwargs)
            except Resolver404:
                pass

        return redirect(next_url)


class ExpensesDashboardView(ProjectRequiredMixin, TemplateView):
    template_name = "expenses.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.project:
            stages = ProjectLifecycleStage.objects.filter(project=self.project)
            cash_requests = MilestoneCashRequest.objects.filter(project=self.project)
            unplanned = UnplannedExpense.objects.filter(project=self.project)
        else:
            stages = ProjectLifecycleStage.objects.all()
            cash_requests = MilestoneCashRequest.objects.all()
            unplanned = UnplannedExpense.objects.all()

        stage_costs = stages.aggregate(total=Sum('incurred_cost'))['total'] or Decimal('0.00')
        cash_request_costs = cash_requests.filter(status='APPROVED').aggregate(total=Sum('amount_requested'))['total'] or Decimal('0.00')
        unplanned_costs = unplanned.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        per_project_expenses = []
        if not self.project:
            for p in Project.objects.all():
                p_stage = ProjectLifecycleStage.objects.filter(project=p).aggregate(total=Sum('incurred_cost'))['total'] or Decimal('0.00')
                p_cash = MilestoneCashRequest.objects.filter(project=p, status='APPROVED').aggregate(total=Sum('amount_requested'))['total'] or Decimal('0.00')
                p_unplanned = UnplannedExpense.objects.filter(project=p).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                if p_stage > 0 or p_cash > 0 or p_unplanned > 0:
                    per_project_expenses.append({
                        'project': p,
                        'stage_costs': p_stage,
                        'cash_request_costs': p_cash,
                        'unplanned_costs': p_unplanned,
                        'total': Decimal(p_stage) + Decimal(p_cash) + Decimal(p_unplanned)
                    })

        context.update({
            'total_stage_costs': stage_costs,
            'total_cash_request_costs': cash_request_costs,
            'total_unplanned_costs': unplanned_costs,
            'total_expenses': Decimal(stage_costs) + Decimal(cash_request_costs) + Decimal(unplanned_costs),
            'per_project_expenses': per_project_expenses,
            'recent_stages': stages.filter(incurred_cost__gt=0).order_by('-completed_date')[:50],
            'recent_cash_requests': cash_requests.filter(status='APPROVED').order_by('-date_requested')[:50],
            'recent_unplanned': unplanned.select_related('reported_by', 'project').order_by('-date_incurred')[:50],
        })
        return context


class UnplannedExpenseCreateView(LoginRequiredMixin, View):
    """Allows any logged-in user to instantly log an unplanned project expense."""
    template_name = 'core/unplanned_expense_form.html'

    def get(self, request):
        projects = Project.objects.all()
        preselect = request.GET.get('project')
        return render(request, self.template_name, {
            'projects': projects,
            'preselect': preselect,
        })

    def post(self, request):
        project_id = request.POST.get('project_id')
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        date_incurred = request.POST.get('date_incurred', '').strip()

        if not project_id or not description or not amount or not date_incurred:
            messages.error(request, "Project, description, amount, and date are all required.")
            return redirect('core:add_unplanned_expense')

        try:
            project = get_object_or_404(Project, pk=project_id)
            UnplannedExpense.objects.create(
                project=project,
                description=description,
                amount=Decimal(amount),
                date_incurred=date_incurred,
                reported_by=request.user,
            )
            messages.success(request, f"Unplanned expense of ₦{Decimal(amount):,.2f} logged for {project.project_code}.")
        except Exception as e:
            messages.error(request, f"Could not save expense: {e}")
        return redirect('core:expenses_dashboard')


class DashboardView(ProjectRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from projects.models import Project, ProjectAllocation, ProjectLifecycleStage
        from contractors.models import Subcontractor, Company, CompanyCompliance
        from logistic.models import SiteStore, MilestoneCashRequest
        
        selected_year = self.request.GET.get('year', '').strip()
        selected_mda = self.request.GET.get('mda', '').strip()

        # 1. Scope determination
        if self.project:
            projects_qs = Project.objects.filter(sn=self.project.sn)
        else:
            projects_qs = Project.objects.all()

        if selected_year:
            projects_qs = projects_qs.filter(created_at__year=selected_year)
        if selected_mda:
            projects_qs = projects_qs.filter(mda__icontains=selected_mda)

        # Prefetch lifecycle stages to eliminate N+1 queries in roadmap rendering
        projects_qs = projects_qs.prefetch_related('lifecycle_stages')

        allocations_qs = ProjectAllocation.objects.filter(project__in=projects_qs)
        cash_requests_qs = MilestoneCashRequest.objects.filter(project__in=projects_qs)
        stores_qs = SiteStore.objects.filter(project__in=projects_qs)
            
        # 2. Role-Based Access Guards
        user = self.request.user
        user_groups = list(user.groups.values_list('name', flat=True)) if user.is_authenticated else []
        is_executive_or_management = (
            user.is_superuser or 
            any(g in ['Executive', 'Management', 'Level 3', 'Level 4'] for g in user_groups)
        )
        if 'Technical/Field' in user_groups:
            is_executive_or_management = False
            
        # 3. Layer A: Executive Financial KPI Cards
        # Total Contract Value Portfolio
        total_contract_value = projects_qs.aggregate(val=Sum('actual_contract_amount'))['val'] or 0.0
        
        # Expected Gross Profit Margin Panel
        total_in_house_benchmark = projects_qs.aggregate(val=Sum('in_house_benchmark'))['val'] or 0.0
        
        if total_contract_value > 0:
            cost_percentage = (Decimal(total_in_house_benchmark) / Decimal(total_contract_value)) * 100
        else:
            cost_percentage = 0.0
        gross_profit_margin = 100.0 - float(cost_percentage)
        
        # Total Disbursed Capital
        total_disbursed_capital = projects_qs.aggregate(
            val=Sum(F('mobilization_received') + F('final_payment_received'))
        )['val'] or 0.0
        
        # Subcontractor Exposure Liability
        subcontractor_exposure = allocations_qs.aggregate(
            val=Sum(F('amount_agreed_with_supplier_contractor') - F('advance_received_by_supplier_contractor'))
        )['val'] or 0.0
        
        # 4. Layer B: Bidding Strategy & File Tracking Pipeline
        active_bidding_pipeline = projects_qs.filter(current_phase='PRE_AWARD')
        
        project_roadmaps = []
        for p in projects_qs:
            stages_list = p.lifecycle_stages.all()
            audit_stage = next((s for s in stages_list if "Head of Audit" in s.stage_name), None)
            procurement_stage = next((s for s in stages_list if "Procurement Office" in s.stage_name), None)
            store_stage = next((s for s in stages_list if "Store Department" in s.stage_name), None)
            finance_stage = next((s for s in stages_list if "Director of Finance" in s.stage_name), None)
            agf_stage = next((s for s in stages_list if "Confirmation of Payment" in s.stage_name or "Certified Status" in s.stage_name or "AGF" in s.stage_name), None)
            
            p_status = (p.payment_status or "").strip().lower()
            p_batch = (p.batch_no_final_payment or "").strip()
            is_alert = (p_status == "uploaded for payment" and not p_batch)
            
            project_roadmaps.append({
                'project_code': p.project_code,
                'project_name': p.project_name,
                'payment_status': p.payment_status,
                'batch_no_final_payment': p.batch_no_final_payment,
                'is_alert': is_alert,
                'stages': [
                    {'name': 'Head of Audit', 'is_completed': audit_stage.is_completed if audit_stage else False, 'notes': audit_stage.notes_or_updates if audit_stage else ''},
                    {'name': 'Procurement Office', 'is_completed': procurement_stage.is_completed if procurement_stage else False, 'notes': procurement_stage.notes_or_updates if procurement_stage else ''},
                    {'name': 'Store Department', 'is_completed': store_stage.is_completed if store_stage else False, 'notes': store_stage.notes_or_updates if store_stage else ''},
                    {'name': 'Director of Finance', 'is_completed': finance_stage.is_completed if finance_stage else False, 'notes': finance_stage.notes_or_updates if finance_stage else ''},
                    {'name': 'AGF Payment', 'is_completed': agf_stage.is_completed if agf_stage else False, 'notes': agf_stage.notes_or_updates if agf_stage else ''},
                ]
            })
            
        # 5. Layer C: Field Operations & Subcontractor Health
        # Bulk query approved cash requests per project in 1 DB hit
        drawn_down_map = dict(
            MilestoneCashRequest.objects.filter(
                project__in=projects_qs, status='APPROVED'
            ).values('project_id').annotate(
                total_drawn=Sum('amount_requested')
            ).values_list('project_id', 'total_drawn')
        )

        # Progress vs Budget Burn-Rate Variance
        project_variances = []
        for p in projects_qs:
            drawn_down = drawn_down_map.get(p.pk, 0.0) or 0.0
            drawdown_rate = (float(drawn_down) / float(p.budget_amount) * 100) if p.budget_amount > 0 else 0.0
            completion_rate = p.execution_level_percentage
            variance = completion_rate - drawdown_rate
            exceeds = drawdown_rate > completion_rate
            project_variances.append({
                'project_code': p.project_code,
                'project_name': p.project_name,
                'budget_amount': p.budget_amount,
                'drawn_down': drawn_down,
                'drawdown_rate': round(drawdown_rate, 2),
                'completion_rate': completion_rate,
                'variance': round(variance, 2),
                'exceeds': exceeds,
            })
            
        # Allocation Spread
        external_pct = allocations_qs.aggregate(total=Sum('sub_contractor_cost_percentage'))['total'] or 0.0
        external_pct = float(external_pct)
        in_house_pct = max(0.0, 100.0 - external_pct)
        
        # 6. Layer D: Field Operations Action Items
        # Pending Milestone Cash Requests
        pending_cash_requests = cash_requests_qs.filter(status='PENDING').select_related('project', 'requested_by')
        
        # Material Deficiency Alerts
        material_alerts = stores_qs.filter(quantity_on_site=0).select_related('project')
        
        # Vendor Compliance Safeguards
        current_year = timezone.now().year
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        
        compliance_alerts = CompanyCompliance.objects.filter(
            year=current_year
        ).filter(
            Q(status__in=['PENDING', 'EXPIRED']) |
            Q(status='APPROVED', expiry_date__lte=thirty_days_later)
        ).select_related('company', 'requirement').order_by('company__name', 'requirement__name')
        
        # Executive Summary Metrics (Matching User Reference Sheets)
        total_projects_count = projects_qs.count()
        total_budget_amount = projects_qs.aggregate(val=Sum('budget_amount'))['val'] or Decimal('0.00')
        total_awarded_amount = projects_qs.aggregate(val=Sum('actual_contract_amount'))['val'] or Decimal('0.00')
        total_in_house_awarded = projects_qs.filter(
            Q(award_letter_and_boq__isnull=False) & ~Q(award_letter_and_boq='')
        ).aggregate(val=Sum('actual_contract_amount'))['val'] or Decimal('0.00')
        
        total_given_out_awarded = max(Decimal('0.00'), total_awarded_amount - total_in_house_awarded)
        total_mobilization_rec = projects_qs.aggregate(val=Sum('mobilization_received'))['val'] or Decimal('0.00')

        # Distinct Agencies
        distinct_mdas = [mda for mda in projects_qs.values_list('mda', flat=True).distinct() if mda]
        agency_count = len(distinct_mdas)
        agency_short_list = ", ".join([mda.split('(')[-1].replace(')', '').strip() if '(' in mda else mda for mda in distinct_mdas])

        # Distinct Year Choices for Filter Dropdown
        year_choices = sorted(
            set(Project.objects.dates('created_at', 'year').values_list('created_at__year', flat=True)),
            reverse=True
        )
        raw_mda_list = [m for m in Project.objects.values_list('mda', flat=True).distinct().order_by('mda') if m]
        mda_choices = []
        seen_shorts = set()
        for m in raw_mda_list:
            short = m.split('(')[-1].split(')')[0].strip() if ('(' in m and ')' in m) else m
            if short not in seen_shorts:
                seen_shorts.add(short)
                mda_choices.append({'full': m, 'short': short})

        # Category Monitoring Matrix (CONSTRUCTION, SUPPLY, EMPOWERMENT, POWER, TRAINING)
        monitoring_matrix = []
        category_list = ['CONSTRUCTION', 'SUPPLY', 'EMPOWERMENT', 'POWER', 'TRAINING']
        awarded_q = (
            Q(actual_contract_amount__gt=0) |
            (Q(award_letter_and_boq__isnull=False) & ~Q(award_letter_and_boq='')) |
            Q(project_status__icontains='AWARD') |
            Q(remarks__icontains='AWARD LETTER')
        )

        for cat_name in category_list:
            if cat_name == 'CONSTRUCTION':
                cat_qs = projects_qs.filter(Q(category__name__iexact='CONSTRUCTION') | Q(category__name__icontains='Civil') | Q(project_type__icontains='CONSTRUCTION'))
            else:
                cat_qs = projects_qs.filter(Q(category__name__iexact=cat_name) | Q(project_type__iexact=cat_name))
            
            c_total = cat_qs.count()
            c_awarded = cat_qs.filter(awarded_q).distinct().count()
            c_awaiting = c_total - c_awarded
            c_budget = cat_qs.aggregate(val=Sum('budget_amount'))['val'] or Decimal('0.00')
            c_awarded_amt = cat_qs.aggregate(val=Sum('actual_contract_amount'))['val'] or Decimal('0.00')
            c_in_house = cat_qs.filter(
                (Q(award_letter_and_boq__isnull=False) & ~Q(award_letter_and_boq='')) |
                Q(remarks__icontains='AWARD LETTER')
            ).aggregate(val=Sum('actual_contract_amount'))['val'] or Decimal('0.00')
            c_given_out = max(Decimal('0.00'), c_awarded_amt - c_in_house)
            c_mob_rec = cat_qs.aggregate(val=Sum('mobilization_received'))['val'] or Decimal('0.00')
            
            monitoring_matrix.append({
                'category_name': cat_name,
                'total_count': c_total,
                'awarded_count': c_awarded,
                'awaiting_count': c_awaiting,
                'budget_amount': c_budget,
                'awarded_amount': c_awarded_amt,
                'in_house_awarded': c_in_house,
                'given_out_awarded': c_given_out,
                'mobilization_received': c_mob_rec,
            })

        context.update({
            'selected_year': selected_year,
            'selected_mda': selected_mda,
            'year_choices': year_choices,
            'mda_choices': mda_choices,
            'is_executive_or_management': is_executive_or_management,
            'total_projects_count': total_projects_count,
            'total_budget_amount': total_budget_amount,
            'total_awarded_amount': total_awarded_amount,
            'total_in_house_awarded': total_in_house_awarded,
            'total_given_out_awarded': total_given_out_awarded,
            'total_mobilization_rec': total_mobilization_rec,
            'agency_count': agency_count,
            'agency_short_list': agency_short_list,
            'monitoring_matrix': monitoring_matrix,
            'total_contract_value': total_contract_value,
            'total_in_house_benchmark': total_in_house_benchmark,
            'cost_percentage': round(cost_percentage, 2),
            'gross_profit_margin': round(gross_profit_margin, 2),
            'total_disbursed_capital': total_disbursed_capital,
            'subcontractor_exposure': subcontractor_exposure,
            'active_bidding_pipeline': active_bidding_pipeline,
            'project_roadmaps': project_roadmaps,
            'project_variances': project_variances,
            'external_pct': external_pct,
            'in_house_pct': in_house_pct,
            'pending_cash_requests': pending_cash_requests,
            'material_alerts': material_alerts,
            'compliance_alerts': compliance_alerts,
            'project': self.project,
            'all_projects': Project.objects.all().order_by('project_code'),
            'total_projects': Project.objects.count(),
            'internal_contractors': Subcontractor.objects.filter(company_type='INTERNAL').count(),
            'external_contractors': Subcontractor.objects.filter(company_type='EXTERNAL').count(),
        })
        return context
