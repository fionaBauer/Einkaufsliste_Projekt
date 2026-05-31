import json
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from recipes.models import Recipe
from shopping.models import ShoppingList, ShoppingListItem
from shopping.utils import to_base_unit, from_base_unit
from .models import MealSlot


def _get_household(request):
    return request.user.households.first()


@login_required
def planner(request):
    household = _get_household(request)
    recipes = Recipe.objects.filter(household=household).order_by("name")

    recipes_data = [
        {
            "id": r.id,
            "name": r.name,
            **({"image": r.image.url} if r.image else {}),
        }
        for r in recipes
    ]

    return render(request, "meal_plan/planner.html", {
        "recipes": recipes,
        "recipes_data": recipes_data,
        "household": household,
    })


@login_required
def slots_api(request):
    """Return meal slots for a date range as JSON."""
    household = _get_household(request)
    start = request.GET.get("start")
    end = request.GET.get("end")

    slots = MealSlot.objects.filter(household=household)
    if start:
        slots = slots.filter(date__gte=start)
    if end:
        slots = slots.filter(date__lte=end)

    data = []
    for slot in slots.select_related("recipe"):
        data.append({
            "id": slot.id,
            "date": slot.date.isoformat(),
            "meal": slot.meal,
            "meal_label": slot.get_meal_display(),
            "recipe_id": slot.recipe_id,
            "recipe_name": slot.recipe.name,
            "recurrence": slot.recurrence,
            "note": slot.note,
        })

    return JsonResponse(data, safe=False)


@login_required
@require_POST
def slot_create(request):
    household = _get_household(request)
    data = json.loads(request.body)

    from datetime import date as date_type
    recipe = get_object_or_404(Recipe, pk=data["recipe_id"], household=household)
    slot = MealSlot.objects.create(
        household=household,
        recipe=recipe,
        date=date_type.fromisoformat(data["date"]),
        meal=data["meal"],
        recurrence=data.get("recurrence", "none"),
        note=data.get("note", ""),
    )

    return JsonResponse({
        "id": slot.id,
        "date": slot.date.isoformat(),
        "meal": slot.meal,
        "meal_label": slot.get_meal_display(),
        "recipe_id": slot.recipe_id,
        "recipe_name": slot.recipe.name,
        "recurrence": slot.recurrence,
        "note": slot.note,
    }, status=201)


@login_required
@require_http_methods(["PATCH"])
def slot_update(request, pk):
    household = _get_household(request)
    slot = get_object_or_404(MealSlot, pk=pk, household=household)
    data = json.loads(request.body)

    from datetime import date as date_type
    if "date" in data:
        slot.date = date_type.fromisoformat(data["date"])
    if "meal" in data:
        slot.meal = data["meal"]
    if "recurrence" in data:
        slot.recurrence = data["recurrence"]
    if "note" in data:
        slot.note = data["note"]
    if "recipe_id" in data:
        recipe = get_object_or_404(Recipe, pk=data["recipe_id"], household=household)
        slot.recipe = recipe

    slot.save()
    return JsonResponse({
        "id": slot.id,
        "date": slot.date.isoformat(),
        "meal": slot.meal,
        "meal_label": slot.get_meal_display(),
        "recipe_id": slot.recipe_id,
        "recipe_name": slot.recipe.name,
        "recurrence": slot.recurrence,
        "note": slot.note,
    })


@login_required
@require_http_methods(["DELETE"])
def slot_delete(request, pk):
    household = _get_household(request)
    slot = get_object_or_404(MealSlot, pk=pk, household=household)
    slot.delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def create_shopping_list(request):
    """Create a shopping list from all meal slots in a given week."""
    household = _get_household(request)
    data = json.loads(request.body)
    start = date.fromisoformat(data["start"])
    end = date.fromisoformat(data["end"])

    slots = MealSlot.objects.filter(
        household=household,
        date__gte=start,
        date__lte=end,
    ).select_related("recipe")

    recipe_ids = list(set(s.recipe_id for s in slots))
    recipes = Recipe.objects.filter(pk__in=recipe_ids).prefetch_related(
        "recipe_ingredients__ingredient"
    )

    # Reuse shopping app logic: create a new list
    from collections import defaultdict
    from decimal import Decimal

    shopping_list = ShoppingList.objects.create(
        household=household,
        name=f"Wochenplan {start.strftime('%d.%m.')}–{end.strftime('%d.%m.%Y')}",
    )

    aggregated = defaultdict(lambda: {"quantity_base": Decimal("0"), "ingredient": None})

    for recipe in recipes:
        for ri in recipe.recipe_ingredients.all():
            key = ri.ingredient_id
            base_qty = to_base_unit(ri.quantity, ri.unit)
            aggregated[key]["quantity_base"] += base_qty
            aggregated[key]["ingredient"] = ri.ingredient

    for ingredient_id, agg in aggregated.items():
        qty, unit = from_base_unit(agg["quantity_base"], agg["ingredient"])
        ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            ingredient=agg["ingredient"],
            quantity=qty,
            unit=unit,
        )

    return JsonResponse({"shopping_list_id": shopping_list.pk}, status=201)