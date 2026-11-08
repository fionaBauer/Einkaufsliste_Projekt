import re

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from deals.services import available_store_names
from deals.views import deals_status_label, start_deal_sync

from .forms import UserSettingsForm
from .models import UserSettings

User = get_user_model()

MAX_FAVORITES = 30


def parse_favorites(text):
    """"Kaffee, Butter\nHähnchen" → ["Kaffee", "Butter", "Hähnchen"] (ohne Dubletten)."""
    favorites = []
    seen = set()
    for part in re.split(r"[,;\n]", text or ""):
        name = " ".join(part.split())[:40]
        if name and name.lower() not in seen:
            seen.add(name.lower())
            favorites.append(name)
    return favorites[:MAX_FAVORITES]


def _render(request, form, settings_obj, error=None):
    stores = sorted(set(available_store_names()) | set(settings_obj.preferred_stores), key=str.lower)
    return render(request, "user_settings/settings.html", {
        "form": form,
        "error": error,
        "stores": stores,
        "selected_stores": settings_obj.preferred_stores,
        "favorites_text": ", ".join(settings_obj.favorite_products),
        "deals_status": deals_status_label(),
    })


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Username speichern
        username = request.POST.get("username", "").strip()
        error = None

        if not username:
            error = "Benutzername darf nicht leer sein."
        elif username != request.user.username and User.objects.filter(username=username).exists():
            error = "Dieser Benutzername ist bereits vergeben."

        if error:
            form = UserSettingsForm(request.POST, instance=settings_obj)
            return _render(request, form, settings_obj, error)

        request.user.username = username
        request.user.save(update_fields=["username"])

        # PLZ, Märkte und Favoriten speichern
        old_postal_code = settings_obj.postal_code
        old_favorites = list(settings_obj.favorite_products)
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            settings_obj = form.save(commit=False)
            settings_obj.preferred_stores = request.POST.getlist("stores")
            settings_obj.favorite_products = parse_favorites(request.POST.get("favorites", ""))
            settings_obj.save()

            # Neue PLZ oder neue Favoriten → passende Angebote gleich nachladen
            if settings_obj.postal_code and (
                settings_obj.postal_code != old_postal_code
                or set(settings_obj.favorite_products) - set(old_favorites)
            ):
                start_deal_sync(request.user)

        messages.success(request, "Einstellungen gespeichert.")
        return redirect("user_settings:settings")

    form = UserSettingsForm(instance=settings_obj)
    return _render(request, form, settings_obj)
