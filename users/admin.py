from django.contrib import admin

from .models import JobTitle, Profile, UserOTP


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ('name', 'permission_group')
    search_fields = ('name', 'permission_group__name')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'phone_number', 'is_2fa_enabled', 'last_active_project')
    list_filter = ('is_2fa_enabled',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_select_related = ('user', 'job_title', 'last_active_project')


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used', 'used_at', 'attempts')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'code')
    readonly_fields = ('created_at', 'used_at')

