from django.conf import settings


def feature_flags(request):
    return {
        "registration_enabled": settings.REGISTRATION_ENABLED,
    }
