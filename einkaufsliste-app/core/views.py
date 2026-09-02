from datetime import date, timedelta
from collections import defaultdict

from accounts.forms import RegisterForm
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from deals.services import get_active_deals, find_deals_for_ingredient
from inventory.models import InventoryItem
from meal_plan.models import MealSlot
from recipes.models import Recipe
from shopping.models import ShoppingList


@login_required
def home(request):
    household = request.user.households.first()
    today = date.today()

    # Today's + upcoming meals
    todays_meals = MealSlot.objects.filter(
        household=household, date=today
    ).select_related("recipe").order_by("meal")

    # Top deals (max 4, with savings)
    top_deals = get_active_deals().filter(
        deal_price__isnull=False,
        original_price__isnull=False,
    ).order_by("deal_price")[:4]

    # Inventory-based recipe suggestions
    inventory_items = InventoryItem.objects.filter(
        household=household
    ).select_related("ingredient")

    has_inventory = inventory_items.exists()
    inventory_ingredient_ids = set(i.ingredient_id for i in inventory_items)

    # Find recipes where most ingredients are in inventory
    recipes = Recipe.objects.filter(
        household=household
    ).prefetch_related("recipe_ingredients__ingredient")

    inventory_suggestions = []
    for recipe in recipes:
        recipe_ingredient_ids = set(
            ri.ingredient_id for ri in recipe.recipe_ingredients.all()
        )
        if not recipe_ingredient_ids:
            continue
        matches = recipe_ingredient_ids & inventory_ingredient_ids
        match_ratio = len(matches) / len(recipe_ingredient_ids)
        if match_ratio >= 0.25 and len(matches) >= 1:
            matched_names = [
                i.ingredient.name for i in inventory_items
                if i.ingredient_id in matches
            ]
            inventory_suggestions.append({
                "recipe": recipe,
                "matched": matched_names[:3],
                "match_count": len(matches),
                "total": len(recipe_ingredient_ids),
            })

    inventory_suggestions.sort(key=lambda x: x["match_count"], reverse=True)
    inventory_suggestions = inventory_suggestions[:3]

    # Shopping list count
    shopping_list = ShoppingList.objects.filter(
        household=household
    ).order_by("-id").first()
    shopping_count = shopping_list.items.count() if shopping_list else 0

    return render(request, "core/home.html", {
        "todays_meals": todays_meals,
        "top_deals": top_deals,
        "inventory_suggestions": inventory_suggestions,
        "shopping_list": shopping_list,
        "shopping_count": shopping_count,
        "today": today,
        "household": household,
        "has_inventory": has_inventory,
    })


def register(request):
    if not settings.REGISTRATION_ENABLED:
        return redirect("login")
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("households:create")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


from django.views.decorators.http import require_POST as _require_POST
from django.http import JsonResponse as _JsonResponse
from django.views.decorators.csrf import csrf_exempt as _csrf_exempt

@login_required
def barcode_lookup(request):
    """Look up a barcode and match against existing ingredients."""
    from core.barcode import lookup_barcode, match_ingredient_name
    from ingredients.models import Ingredient

    barcode = request.GET.get("barcode", "").strip()
    if not barcode:
        return _JsonResponse({"found": False, "error": "Kein Barcode angegeben"}, status=400)

    result = lookup_barcode(barcode)

    if not result["found"]:
        return _JsonResponse({"found": False, "barcode": barcode})

    # Match against existing ingredients
    household = request.user.households.first()
    all_ingredients = Ingredient.objects.all()
    matched_name = match_ingredient_name(result["product_name"], all_ingredients)

    # Check if ingredient already exists
    from ingredients.models import Unit
    existing = Ingredient.objects.filter(name__iexact=matched_name).first()

    # Check inventory
    from inventory.models import InventoryItem
    inventory_item = None
    if existing and household:
        inventory_item = InventoryItem.objects.filter(
            household=household,
            ingredient=existing
        ).first()

    return _JsonResponse({
        "found": True,
        "barcode": barcode,
        "product_name": result["product_name"],
        "matched_name": matched_name,
        "brand": result.get("brand", ""),
        "quantity": result.get("quantity", ""),
        "ingredient_id": existing.id if existing else None,
        "in_inventory": inventory_item is not None,
        "inventory_quantity": str(inventory_item.quantity) if inventory_item and inventory_item.quantity else None,
        "inventory_unit": inventory_item.unit if inventory_item else None,
        "inventory_id": inventory_item.id if inventory_item else None,
    })