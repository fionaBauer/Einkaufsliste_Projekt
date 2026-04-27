from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ingredients.models import IngredientCategory
from .forms import InventoryItemForm
from .models import InventoryItem

from recipes.views import _from_base_unit, _to_base_unit

from decimal import Decimal
from django.http import JsonResponse
from recipes.models import Recipe


@login_required
def inventory_list(request):
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name_asc")

    inventory_items = list(InventoryItem.objects.select_related("ingredient").all())

    if search_query:
        inventory_items = [
            item for item in inventory_items
            if search_query.lower() in item.ingredient.name.lower()
        ]

    if sort == "name_desc":
        inventory_items.sort(key=lambda item: item.ingredient.name.lower(), reverse=True)
    elif sort == "quantity_asc":
        inventory_items.sort(
            key=lambda item: (
                item.quantity is None,
                item.quantity if item.quantity is not None else 0,
                item.ingredient.name.lower(),
            )
        )
    elif sort == "quantity_desc":
        inventory_items.sort(
            key=lambda item: (
                item.quantity is None,
                -(float(item.quantity) if item.quantity is not None else 0),
                item.ingredient.name.lower(),
            )
        )
    else:
        inventory_items.sort(key=lambda item: item.ingredient.name.lower())

    grouped_inventory_items = OrderedDict()

    for category_value, category_label in IngredientCategory.choices:
        category_items = [item for item in inventory_items if item.ingredient.category == category_value]
        if category_items:
            grouped_inventory_items[category_label] = category_items

    create_form = InventoryItemForm(exclude_used_ingredients=True)
    edit_form = None
    edit_item_id = None
    create_modal_open = False
    edit_modal_open = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            create_form = InventoryItemForm(request.POST, exclude_used_ingredients=True)
            if create_form.is_valid():
                create_form.save()
                return redirect("inventory:list")
            create_modal_open = True

        elif action == "edit":
            item_id = request.POST.get("item_id")
            inventory_item = get_object_or_404(InventoryItem, pk=item_id)
            edit_form = InventoryItemForm(request.POST, instance=inventory_item)
            edit_item_id = inventory_item.id

            if edit_form.is_valid():
                edit_form.save()
                return redirect("inventory:list")
            edit_modal_open = True

        elif action == "delete":
            item_id = request.POST.get("item_id")
            inventory_item = get_object_or_404(InventoryItem, pk=item_id)
            inventory_item.delete()
            return redirect("inventory:list")

    if edit_form is None:
        edit_form = InventoryItemForm()

    context = {
        "inventory_items": inventory_items,
        "grouped_inventory_items": grouped_inventory_items,
        "create_form": create_form,
        "edit_form": edit_form,
        "edit_item_id": edit_item_id,
        "create_modal_open": create_modal_open,
        "edit_modal_open": edit_modal_open,
        "search_query": search_query,
        "sort": sort,
        "recipes_for_consume": Recipe.objects.order_by("name"),
        "sort_options": [
            ("name_asc", "Name A–Z"),
            ("name_desc", "Name Z–A"),
            ("quantity_asc", "Menge aufsteigend"),
            ("quantity_desc", "Menge absteigend"),
        ],
    }
    return render(request, "inventory/inventory_list.html", context)

@login_required
def recipe_consume_preview(request):
    recipe_id = request.GET.get("recipe_id")
    target_servings = request.GET.get("servings")

    if not recipe_id:
        return JsonResponse({
            "success": False,
            "error": "Bitte wähle ein Rezept aus.",
        }, status=400)

    try:
        recipe = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Rezept wurde nicht gefunden.",
        }, status=404)

    try:
        target_servings = int(target_servings) if target_servings else recipe.servings
        if target_servings < 1:
            target_servings = recipe.servings
    except (TypeError, ValueError):
        target_servings = recipe.servings

    factor = recipe.scale_factor(target_servings)

    preview_items = []

    inventory_items = {
        item.ingredient_id: item
        for item in InventoryItem.objects.select_related("ingredient")
    }

    for recipe_item in recipe.recipe_ingredients.all():
        scaled_quantity = recipe_item.quantity * factor
        inventory_item = inventory_items.get(recipe_item.ingredient_id)

        can_be_consumed = False
        inventory_display = "Nicht im Inventar"
        status_label = "Nicht im Inventar"
        status_type = "muted"

        if inventory_item:
            if inventory_item.quantity is None:
                inventory_display = "Menge unbekannt"
                status_label = "Menge unbekannt"
                status_type = "muted"
            elif inventory_item.unit in ["el", "tl"]:
                inventory_display = f"{inventory_item.quantity} {inventory_item.unit}"
                status_label = "EL/TL nicht automatisch"
                status_type = "warn"
            else:
                inventory_display = f"{inventory_item.quantity} {inventory_item.unit}"
                can_be_consumed = True
                status_label = "Wird angepasst"
                status_type = "ok"

        if recipe_item.unit in ["el", "tl"]:
            can_be_consumed = False
            status_label = "EL/TL nicht automatisch"
            status_type = "warn"

        if recipe_item.quantity is None:
            can_be_consumed = False
            status_label = "Rezeptmenge unbekannt"
            status_type = "muted"

        preview_items.append({
            "ingredient_id": recipe_item.ingredient.id,
            "ingredient_name": recipe_item.ingredient.name,
            "recipe_quantity": str(scaled_quantity),
            "recipe_unit": recipe_item.unit,
            "inventory_display": inventory_display,
            "checked": can_be_consumed,
            "disabled": not can_be_consumed,
            "status_label": status_label,
            "status_type": status_type,
        })

    return JsonResponse({
        "success": True,
        "recipe": {
            "id": recipe.id,
            "name": recipe.name,
        },
        "servings": target_servings,
        "items": preview_items,
    })

@login_required
def apply_recipe_consumption(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Ungültige Anfrage.",
        }, status=405)

    try:
        import json
        data = json.loads(request.body)

        recipe_id = data.get("recipe_id")
        target_servings = data.get("servings")
        selected_ingredient_ids = data.get("ingredient_ids", [])

        if not recipe_id:
            return JsonResponse({
                "success": False,
                "error": "Bitte wähle ein Rezept aus.",
            }, status=400)

        try:
            recipe = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Rezept wurde nicht gefunden.",
            }, status=404)

        try:
            target_servings = int(target_servings) if target_servings else recipe.servings
            if target_servings < 1:
                target_servings = recipe.servings
        except (TypeError, ValueError):
            target_servings = recipe.servings

        factor = recipe.scale_factor(target_servings)

        inventory_items = {
            item.ingredient_id: item
            for item in InventoryItem.objects.select_related("ingredient")
        }

        selected_ingredient_ids = {int(pk) for pk in selected_ingredient_ids}
        changed_count = 0
        removed_count = 0

        for recipe_item in recipe.recipe_ingredients.all():
            ingredient_id = recipe_item.ingredient_id

            if ingredient_id not in selected_ingredient_ids:
                continue

            inventory_item = inventory_items.get(ingredient_id)
            if not inventory_item:
                continue

            if inventory_item.quantity is None:
                continue

            scaled_quantity = recipe_item.quantity * factor

            if recipe_item.unit in ["el", "tl"]:
                continue

            recipe_base_quantity, recipe_base_unit = _to_base_unit(scaled_quantity, recipe_item.unit)
            inventory_base_quantity, inventory_base_unit = _to_base_unit(
                inventory_item.quantity,
                inventory_item.unit,
            )

            if recipe_base_unit != inventory_base_unit:
                continue

            new_base_quantity = inventory_base_quantity - recipe_base_quantity

            if new_base_quantity <= 0:
                inventory_item.delete()
                removed_count += 1
                changed_count += 1
                continue

            display_quantity, display_unit = _from_base_unit(new_base_quantity, inventory_base_unit)
            inventory_item.quantity = display_quantity
            inventory_item.unit = display_unit
            inventory_item.save(update_fields=["quantity", "unit", "updated_at"])
            changed_count += 1

        return JsonResponse({
            "success": True,
            "message": f"{changed_count} Inventar-Einträge wurden angepasst, {removed_count} entfernt.",
        })

    except Exception as error:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": f"Verbrauch konnte nicht angewendet werden: {str(error)}",
        }, status=500)