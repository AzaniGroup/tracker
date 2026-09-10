def projects_context(request):
    from projects.models import Project
    return {
        'all_projects': Project.objects.all()
    }


def users_context(request):
    management_levels = ('Level 4',)
    user = getattr(request, 'user', None)
    can_manage_users = False
    has_2fa_enabled = True
    if user and user.is_authenticated:
        can_manage_users = user.is_superuser or user.groups.filter(name__in=management_levels).exists()
        profile = getattr(user, 'profile', None)
        if profile is not None:
            has_2fa_enabled = profile.is_2fa_enabled
        else:
            has_2fa_enabled = False
    return {
        'can_manage_users': can_manage_users,
        'has_2fa_enabled': has_2fa_enabled,
    }
