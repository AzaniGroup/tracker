from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import JobTitleForm, SelfProfileUpdateForm, UserCreateForm, UserUpdateForm
from .models import JobTitle, Profile


User = get_user_model()
MANAGEMENT_LEVELS = ('Level 4',)


class ManagementAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=MANAGEMENT_LEVELS).exists()


class ProfileView(LoginRequiredMixin, View):
    template_name = 'users/profile.html'

    def get(self, request):
        profile, _ = Profile.objects.select_related('job_title', 'last_active_project').get_or_create(user=request.user)
        form = SelfProfileUpdateForm(instance=request.user)
        context = {
            'profile': profile,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        profile, _ = Profile.objects.select_related('job_title', 'last_active_project').get_or_create(user=request.user)
        form = SelfProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            if form.cleaned_data.get('new_password'):
                update_session_auth_hash(request, user)
                messages.success(request, 'Your profile details and password have been successfully updated!')
            else:
                messages.success(request, 'Your profile details have been successfully updated!')
            return redirect('users:profile')

        context = {
            'profile': profile,
            'form': form,
        }
        return render(request, self.template_name, context)


def toggle_2fa_view(request):
    """Allows authenticated user to toggle or activate 2FA on their profile."""
    if not request.user.is_authenticated:
        return redirect('core:login')
    
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.is_2fa_enabled = not profile.is_2fa_enabled
    profile.save()
    
    if profile.is_2fa_enabled:
        messages.success(request, "Two-Factor Authentication (2FA) has been successfully activated for your account.")
    else:
        messages.warning(request, "Two-Factor Authentication (2FA) is currently deactivated.")
        
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse_lazy('users:profile')
    return redirect(next_url)


class UserListView(ManagementAccessMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.select_related('profile', 'profile__job_title').prefetch_related('groups').order_by('username')


class UserCreateView(ManagementAccessMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        user = form.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.job_title = form.cleaned_data.get('job_title')
        profile.phone_number = form.cleaned_data.get('phone_number')
        profile.last_active_project = form.cleaned_data.get('last_active_project')
        profile.save()
        self._sync_user_groups(user, profile.job_title)
        messages.success(self.request, 'User created successfully.')
        return redirect(self.success_url)

    def _sync_user_groups(self, user, job_title):
        user.groups.clear()
        if job_title and job_title.permission_group:
            user.groups.add(job_title.permission_group)


class UserUpdateView(ManagementAccessMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def get_initial(self):
        initial = super().get_initial()
        profile = getattr(self.object, 'profile', None)
        if profile:
            initial.update(
                {
                    'job_title': profile.job_title,
                    'phone_number': profile.phone_number,
                    'last_active_project': profile.last_active_project,
                }
            )
        return initial

    def form_valid(self, form):
        user = form.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.job_title = form.cleaned_data.get('job_title')
        profile.phone_number = form.cleaned_data.get('phone_number')
        profile.last_active_project = form.cleaned_data.get('last_active_project')
        profile.save()
        user.groups.clear()
        if profile.job_title and profile.job_title.permission_group:
            user.groups.add(profile.job_title.permission_group)
        messages.success(self.request, 'User updated successfully.')
        return redirect(self.success_url)


class UserDeleteView(ManagementAccessMixin, DeleteView):
    model = User
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('users:user_list')


class JobTitleListView(ManagementAccessMixin, ListView):
    model = JobTitle
    template_name = 'users/jobtitle_list.html'
    context_object_name = 'job_titles'


class JobTitleCreateView(ManagementAccessMixin, CreateView):
    model = JobTitle
    form_class = JobTitleForm
    template_name = 'users/jobtitle_form.html'
    success_url = reverse_lazy('users:jobtitle_list')


class JobTitleUpdateView(ManagementAccessMixin, UpdateView):
    model = JobTitle
    form_class = JobTitleForm
    template_name = 'users/jobtitle_form.html'
    success_url = reverse_lazy('users:jobtitle_list')


class JobTitleDeleteView(ManagementAccessMixin, DeleteView):
    model = JobTitle
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('users:jobtitle_list')
