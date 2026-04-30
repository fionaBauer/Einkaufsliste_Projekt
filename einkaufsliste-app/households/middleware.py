from django.shortcuts import redirect
from django.urls import reverse


EXEMPT_PREFIXES = (
    "/accounts/",
    "/households/",
    "/admin/",
)


class HouseholdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            is_exempt = any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)
            if not is_exempt and not request.user.households.exists():
                return redirect(reverse("households:create"))
        return self.get_response(request)
