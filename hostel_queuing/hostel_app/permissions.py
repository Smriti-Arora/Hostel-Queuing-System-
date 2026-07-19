from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import StaffProfile


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return StaffProfile.ROLE_ADMIN
    profile = getattr(user, 'staff_profile', None)
    if profile:
        return profile.role
    return None


def home_url_for_role(role):
    if role == StaffProfile.ROLE_GATE:
        return 'scan_qr'
    if role == StaffProfile.ROLE_MESS:
        return 'scan_qr_for_mess'
    return 'student_list'


def role_required(*allowed_roles):
    """Allow listed roles; admin always has access."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role == StaffProfile.ROLE_ADMIN or role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access that page.')
            return redirect(home_url_for_role(role))

        return _wrapped

    return decorator
