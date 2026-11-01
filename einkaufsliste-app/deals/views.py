import logging
import threading
from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from households.models import Household
from ingredients.models import Ingredient
from recipes.models import RecipeIngredient
from shopping.models import ShoppingList

from .models import DealSource
from .services import deal_sort_key, find_deals_for_ingredient, get_active_deals
from .sync import sync_marktguru, SyncAlreadyRunning, STALE_SYNC_LOCK_AFTER
from .providers.marktguru import MarktguruProvider

logger = logging.getLogger(__name__)

# Angebote gelten als veraltet → beim Öffnen der Seite automatisch im Hintergrund neu laden
AUTO_REFRESH_AFTER = timedelta(hours=24)
MAX_RECIPE_GROUPS = 12
BERLIN = ZoneInfo("Europe/Berlin")


def _sync_marktguru_in_background(zip_code, household_id=None):
    """Wird in einem eigenen Thread ausgefuehrt - Exceptions hier wuerden sonst
    komplett unbemerkt verschwinden, da die Response laengst zurueckgegangen ist."""
    try:
        household = Household.objects.filter(pk=household_id).first() if household_id else None
        sync_marktguru(zip_code, household=household)
    except SyncAlreadyRunning:
        pass  # erwarteter Fall (Doppelklick o.ae.), kein echter Fehler
    except Exception:
        logger.exception("MarktGuru-Sync fehlgeschlagen (PLZ %s)", zip_code)
    finally:
        close_old_connections()


def _get_source():
    return DealSource.objects.filter(name=MarktguruProvider.source_name).first()


def _is_syncing(source):
    if not source or not source.is_syncing:
        return False
    return bool(source.sync_started_at) and source.sync_started_at >= timezone.now() - STALE_SYNC_LOCK_AFTER


def _synced_label(source):
    if not source or not source.last_synced_at:
        return ""
    local = source.last_synced_at.astimezone(BERLIN)
    today = timezone.now().astimezone(BERLIN).date()
    if local.date() == today:
        return f"heute, {local:%H:%M} Uhr"
    if local.date() == today - timedelta(days=1):
        return f"gestern, {local:%H:%M} Uhr"
    return f"{local:%d.%m.}, {local:%H:%M} Uhr"


def _group_deals(ingredients, deals, per_group, recipes_for=None):
    """recipes_for: {ingredient_id: [{"id", "name"}, …]} – für den Hinweis "für Rezept X"."""
    groups = []
    for ingredient in ingredients:
        matched = find_deals_for_ingredient(ingredient, deals)[:per_group]
        if matched:
            recipes = (recipes_for or {}).get(ingredient.id, [])
            groups.append({
                "ingredient": ingredient,
                "deals": matched,
                "recipes": recipes[:2],
                "more_recipes": max(0, len(recipes) - 2),
            })
    return groups


def _household_recipes_by_ingredient(household):
    """{ingredient_id: [{"id", "name"}, …]} für alle Rezepte des Haushalts."""
    mapping = defaultdict(list)
    seen = set()
    rows = (
        RecipeIngredient.objects.filter(recipe__household=household)
        .values_list("ingredient_id", "recipe_id", "recipe__name")
        .order_by("recipe__name")
    )
    for ingredient_id, recipe_id, recipe_name in rows:
        if (ingredient_id, recipe_id) not in seen:
            seen.add((ingredient_id, recipe_id))
            mapping[ingredient_id].append({"id": recipe_id, "name": recipe_name})
    return mapping


@login_required
def deal_list(request):
    household = request.user.households.first()
    search = request.GET.get("search", "").strip()
    store_id = request.GET.get("store", "").strip()
    show_all = request.GET.get("all") == "1"

    all_deals = list(get_active_deals())
    stores = sorted({deal.store_id: deal.store for deal in all_deals}.values(), key=lambda s: s.name.lower())
    deals = [d for d in all_deals if str(d.store_id) == store_id] if store_id else all_deals

    results = None
    list_groups = []
    recipe_groups = []

    if search:
        needle = search.lower()
        results = sorted((d for d in deals if needle in d.title.lower()), key=deal_sort_key)
    elif show_all:
        results = sorted(deals, key=lambda d: (d.store.name.lower(), deal_sort_key(d)))
    else:
        recipes_by_ingredient = _household_recipes_by_ingredient(household)
        existing_recipe_ids = {r["id"] for rs in recipes_by_ingredient.values() for r in rs}

        # 1. Was auf der Einkaufsliste steht – mit den Rezepten, aus denen der Artikel kam
        shopping_list = ShoppingList.objects.filter(household=household).first()
        list_ingredients = []
        list_recipes = defaultdict(list)
        if shopping_list:
            seen = set()
            for item in shopping_list.items.select_related("ingredient").order_by("ingredient__name"):
                if item.ingredient_id not in seen:
                    seen.add(item.ingredient_id)
                    list_ingredients.append(item.ingredient)
                for source in item.source_details or []:
                    recipe_id = source.get("recipe_id")
                    known = {r["id"] for r in list_recipes[item.ingredient_id]}
                    # nur Rezepte, die es noch gibt (gelöschte würden ins Leere verlinken)
                    if recipe_id in existing_recipe_ids and recipe_id not in known:
                        list_recipes[item.ingredient_id].append({"id": recipe_id, "name": source.get("recipe_name", "")})
        list_groups = _group_deals(list_ingredients, deals, per_group=3, recipes_for=list_recipes)

        # 2. Zutaten aus den eigenen Rezepten (ohne die, die schon auf der Liste stehen)
        recipe_ingredients = (
            Ingredient.objects.filter(ingredient_recipes__recipe__household=household)
            .exclude(id__in=[i.id for i in list_ingredients])
            .distinct()
            .order_by("name")
        )
        recipe_groups = _group_deals(
            recipe_ingredients, deals, per_group=2, recipes_for=recipes_by_ingredient,
        )[:MAX_RECIPE_GROUPS]

    source = _get_source()
    syncing = _is_syncing(source)
    settings_obj = getattr(request.user, "settings", None)
    postal_code = getattr(settings_obj, "postal_code", "") or ""
    # Veraltet = länger als einen Tag her ODER keine gültigen Angebote mehr (alle abgelaufen)
    is_stale = (
        not all_deals
        or not source
        or not source.last_synced_at
        or source.last_synced_at < timezone.now() - AUTO_REFRESH_AFTER
    )

    return render(request, "deals/deal_list.html", {
        "results": results,
        "list_groups": list_groups,
        "recipe_groups": recipe_groups,
        "stores": stores,
        "search": search,
        "selected_store": store_id,
        "show_all": show_all,
        "deal_count": len(all_deals),
        "postal_code": postal_code,
        "synced_label": _synced_label(source),
        "syncing": syncing,
        "auto_refresh": bool(postal_code) and is_stale and not syncing,
    })


@login_required
def sync_deals_view(request):
    if request.method != "POST":
        return redirect("deals:list")

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    settings_obj = getattr(request.user, "settings", None)

    if not settings_obj or not settings_obj.postal_code:
        error = "Bitte speichere zuerst deine Postleitzahl."
        if is_ajax:
            return JsonResponse({"ok": False, "error": error, "redirect": reverse("user_settings:settings")}, status=400)
        messages.error(request, error)
        return redirect("user_settings:settings")

    zip_code = settings_obj.postal_code

    # Nur ein optimistischer Hinweis fuer sofortiges Feedback - die eigentliche,
    # race-sichere Pruefung passiert atomar in sync_marktguru() selbst.
    if _is_syncing(_get_source()):
        if is_ajax:
            return JsonResponse({"ok": True, "already_running": True})
        messages.info(request, "Es läuft bereits eine Aktualisierung der Rabatte im Hintergrund.")
        return redirect("deals:list")

    household = request.user.households.first()
    try:
        threading.Thread(
            target=_sync_marktguru_in_background,
            args=(zip_code, household.pk if household else None),
            daemon=True,
        ).start()
    except Exception as error:
        if is_ajax:
            return JsonResponse({"ok": False, "error": f"Rabatte konnten nicht geladen werden: {error}"}, status=500)
        messages.error(request, f"Rabatte konnten nicht geladen werden: {error}")
        return redirect("deals:list")

    if is_ajax:
        return JsonResponse({"ok": True})
    messages.success(request, "Rabatte werden jetzt im Hintergrund aktualisiert.")
    return redirect("deals:list")


@login_required
def sync_status(request):
    """Für die Ladeanzeige: wird während des Aktualisierens jede Sekunde abgefragt."""
    source = _get_source()
    if not source:
        return JsonResponse({"syncing": False, "done": 0, "total": 0, "count": 0, "error": ""})
    return JsonResponse({
        "syncing": _is_syncing(source),
        "done": source.sync_done,
        "total": source.sync_total,
        "count": source.last_sync_count,
        "error": source.last_sync_error,
        "synced_label": _synced_label(source),
    })
