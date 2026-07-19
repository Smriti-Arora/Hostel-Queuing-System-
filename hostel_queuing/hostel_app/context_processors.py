from .permissions import get_user_role, home_url_for_role


def role_context(request):
    role = get_user_role(request.user) if hasattr(request, 'user') else None
    return {
        'user_role': role,
        'is_admin_user': role == 'admin',
        'is_gate_user': role in ('admin', 'gate'),
        'is_mess_user': role in ('admin', 'mess'),
        'role_home': home_url_for_role(role),
    }
