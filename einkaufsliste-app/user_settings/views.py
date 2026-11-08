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


def _settings_for(user):
    settings_obj, _ = UserSettings.objects.get_or_create(user=user)
    return settings_obj


@login_required
def settings_view(request):
    """Übersicht: je Bereich eine Zeile mit dem aktuellen Stand, Tippen öffnet die Unterseite."""
    settings_obj = _settings_for(request.user)
    household = request.user.households.first()

    stores = settings_obj.preferred_stores
    favorites = settings_obj.favorite_products
    deals_summary = [f"{len(stores)} Läden" if len(stores) != 1 else "1 Laden"] if stores else ["Alle Läden"]
    if favorites:
        deals_summary.append(f"{len(favorites)} Favorit{'en' if len(favorites) != 1 else ''}")

    account_summary = request.user.username
    if settings_obj.postal_code:
        account_summary += f" · PLZ {settings_obj.postal_code}"

    household_summary = ""
    if household:
        members = household.members.count()
        household_summary = f"{household.name} · {members} Mitglied{'er' if members != 1 else ''}"

    return render(request, "user_settings/settings.html", {
        "account_summary": account_summary,
        "household_summary": household_summary,
        "deals_summary": " · ".join(deals_summary),
    })


@login_required
def account_view(request):
    settings_obj = _settings_for(request.user)
    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        # vor dem Formular merken – is_valid() schreibt die neuen Werte schon ins Objekt
        old_postal_code = settings_obj.postal_code
        form = UserSettingsForm(request.POST, instance=settings_obj)

        if not username:
            error = "Benutzername darf nicht leer sein."
        elif username != request.user.username and User.objects.filter(username=username).exists():
            error = "Dieser Benutzername ist bereits vergeben."
        elif form.is_valid():
            request.user.username = username
            request.user.save(update_fields=["username"])
            settings_obj = form.save()
            # Neue PLZ → Angebote der neuen Umgebung gleich laden
            if settings_obj.postal_code and settings_obj.postal_code != old_postal_code:
                start_deal_sync(request.user)
            messages.success(request, "Gespeichert.")
            return redirect("user_settings:settings")
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, "user_settings/account.html", {"form": form, "error": error})


@login_required
def deals_view(request):
    settings_obj = _settings_for(request.user)

    if request.method == "POST":
        old_favorites = set(settings_obj.favorite_products)
        settings_obj.preferred_stores = request.POST.getlist("stores")
        settings_obj.favorite_products = parse_favorites(request.POST.get("favorites", ""))
        settings_obj.save(update_fields=["preferred_stores", "favorite_products"])

        # Neue Favoriten → passende Angebote gleich nachladen
        if settings_obj.postal_code and set(settings_obj.favorite_products) - old_favorites:
            start_deal_sync(request.user)

        messages.success(request, "Gespeichert.")
        return redirect("user_settings:settings")

    stores = sorted(set(available_store_names()) | set(settings_obj.preferred_stores), key=str.lower)
    return render(request, "user_settings/deals.html", {
        "stores": stores,
        "selected_stores": settings_obj.preferred_stores,
        "favorites_text": ", ".join(settings_obj.favorite_products),
        "postal_code": settings_obj.postal_code,
        "deals_status": deals_status_label(),
    })
