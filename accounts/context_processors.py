from .models import ActiveUsersCounter


def active_users_count(request):
    if not request.user.is_authenticated:
        return {"active_users_count": None}

    return {"active_users_count": ActiveUsersCounter.get_next_value()}
