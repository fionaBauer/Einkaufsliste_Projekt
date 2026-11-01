from django.conf import settings


def current_household(request):
    """Haushalt des Nutzers, einmal pro Request (Sidebar und Mehr-Menü brauchen den Namen)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"current_household": None}
    if not hasattr(request, "_current_household"):
        request._current_household = user.households.first()
    return {"current_household": request._current_household}


def feature_flags(request):
    return {
        "registration_enabled": settings.REGISTRATION_ENABLED,
    }
