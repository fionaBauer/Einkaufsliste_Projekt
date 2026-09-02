from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from ingredients.models import Ingredient, IngredientCategory
from .forms import InventoryItemForm
from .models import InventoryItem

from recipes.views import _from_base_unit, _to_base_unit

from decimal import Decimal
from django.http import JsonResponse
from recipes.models import Recipe


@login_required
def inventory_list(request):
    household = request.user.households.first()
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name_asc")

    inventory_items = list(
        InventoryItem.objects.filter(household=household).select_related("ingredient")
    )

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

    create_form = InventoryItemForm(household=household, exclude_used_ingredients=True)
    edit_form = None
    edit_item_id = None
    create_modal_open = False
    edit_modal_open = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            create_form = InventoryItemForm(request.POST, household=household, exclude_used_ingredients=True)
            if create_form.is_valid():
                item = create_form.save(commit=False)
                item.household = household
                item.save()
                return redirect("inventory:list")
            create_modal_open = True

        elif action == "edit":
            item_id = request.POST.get("item_id")
            inventory_item = get_object_or_404(InventoryItem, pk=item_id, household=household)
            edit_form = InventoryItemForm(request.POST, instance=inventory_item, household=household)
            edit_item_id = inventory_item.id

            if edit_form.is_valid():
                edit_form.save()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": True})
                return redirect("inventory:list")
            edit_modal_open = True

        elif action == "delete":
            item_id = request.POST.get("item_id")
            inventory_item = get_object_or_404(InventoryItem, pk=item_id, household=household)
            inventory_item.delete()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True})
            return redirect("inventory:list")

    if edit_form is None:
        edit_form = InventoryItemForm(household=household)

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
        "recipes_for_consume": Recipe.objects.filter(household=household).order_by("name"),
        "all_ingredients_json": list(Ingredient.objects.values("id", "name").order_by("name")),
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
    household = request.user.households.first()
    recipe_id = request.GET.get("recipe_id")
    target_servings = request.GET.get("servings")

    if not recipe_id:
        return JsonResponse({
            "success": False,
            "error": "Bitte wähle ein Rezept aus.",
        }, status=400)

    try:
        recipe = Recipe.objects.filter(household=household).prefetch_related("recipe_ingredients__ingredient").get(pk=recipe_id)
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
        for item in InventoryItem.objects.filter(household=household).select_related("ingredient")
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

        household = request.user.households.first()
        recipe_id = data.get("recipe_id")
        target_servings = data.get("servings")
        selected_ingredient_ids = data.get("ingredient_ids", [])

        if not recipe_id:
            return JsonResponse({
                "success": False,
                "error": "Bitte wähle ein Rezept aus.",
            }, status=400)

        try:
            recipe = Recipe.objects.filter(household=household).prefetch_related("recipe_ingredients__ingredient").get(pk=recipe_id)
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
            for item in InventoryItem.objects.filter(household=household).select_related("ingredient")
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


@login_required
@require_POST
def barcode_add(request):
    """Add a scanned product to inventory."""
    import json
    data = json.loads(request.body)
    household = request.user.households.first()

    matched_name = (data.get("matched_name") or "").strip()
    product_name = (data.get("product_name") or "").strip()
    quantity = data.get("quantity")
    unit = data.get("unit") or "g"

    if not matched_name:
        return JsonResponse({"success": False, "error": "Kein Name"}, status=400)

    from recipes.views import _get_or_create_matching_ingredient
    from ingredients.models import Unit as UnitChoices
    ingredient = _get_or_create_matching_ingredient(matched_name, unit)

    try:
        from decimal import Decimal
        qty = Decimal(str(quantity)) if quantity else None
    except Exception:
        qty = None

    valid_units = [u[0] for u in UnitChoices.choices]
    if unit not in valid_units:
        unit = ingredient.default_unit or "g"

    # Add note with exact product name if different
    notes = product_name if product_name.lower() != matched_name.lower() else ""

    item, created = InventoryItem.objects.get_or_create(
        household=household,
        ingredient=ingredient,
        defaults={"quantity": qty, "unit": unit, "notes": notes},
    )

    if not created and qty:
        from decimal import Decimal
        item.quantity = (item.quantity or Decimal("0")) + qty
        if notes:
            item.notes = notes
        item.save()

    return JsonResponse({"success": True, "created": created})


RECEIPT_MAX_UPLOAD_SIZE = 15 * 1024 * 1024
RECEIPT_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


@login_required
@require_POST
def receipt_scan(request):
    """Kassenzettel/Einkaufszettel hochladen, per GPT-4o auslesen und exakt mit Zutaten abgleichen."""
    from core.receipt_scan import extract_receipt_items, prepare_receipt_input
    from decimal import Decimal
    from ingredients.models import Ingredient, Unit as UnitChoices

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"success": False, "error": "Keine Datei erhalten."}, status=400)

    if uploaded_file.size > RECEIPT_MAX_UPLOAD_SIZE:
        return JsonResponse({"success": False, "error": "Datei ist zu groß (max. 15 MB)."}, status=400)

    content_type = uploaded_file.content_type or ""
    file_bytes = uploaded_file.read()

    if content_type not in RECEIPT_ALLOWED_CONTENT_TYPES and file_bytes[:4] != b"%PDF":
        return JsonResponse({"success": False, "error": "Nicht unterstütztes Dateiformat."}, status=400)

    try:
        prepared_input = prepare_receipt_input(file_bytes, content_type)
        raw_items = extract_receipt_items(prepared_input)
    except Exception:
        return JsonResponse({"success": False, "error": "Kassenzettel konnte nicht ausgelesen werden."}, status=500)

    valid_units = {u[0] for u in UnitChoices.choices}
    # Exaktes Matching (case-insensitive) statt Fuzzy-Matching: vermeidet Fehltreffer
    # wie "Pesto Paprika" -> "Paprika". Kein exakter Treffer -> Nutzer wählt manuell.
    ingredients_by_name = {i.name.lower(): i for i in Ingredient.objects.all()}

    items = []
    for raw_item in raw_items:
        generic_name = (raw_item.get("name") or "").strip()
        if not generic_name:
            continue

        raw_name = (raw_item.get("raw_name") or generic_name).strip()
        existing = ingredients_by_name.get(generic_name.lower())

        unit = raw_item.get("unit") or "pcs"
        if unit not in valid_units:
            unit = "pcs"

        try:
            quantity = str(Decimal(str(raw_item.get("quantity") or "1")))
        except Exception:
            quantity = "1"

        items.append({
            "raw_name": raw_name,
            "generic_name": generic_name,
            "quantity": quantity,
            "unit": unit,
            "matched_ingredient_id": existing.id if existing else None,
        })

    return JsonResponse({"success": True, "items": items})


@login_required
@require_POST
def receipt_confirm(request):
    """Bestätigte Kassenzettel-Artikel (mit vom Nutzer gewählter Zutat) als Inventar-Einträge anlegen/aktualisieren."""
    import json
    from decimal import Decimal

    from ingredients.models import Ingredient, Unit as UnitChoices

    household = request.user.households.first()

    try:
        data = json.loads(request.body)
        items = data.get("items", [])
    except Exception:
        return JsonResponse({"success": False, "error": "Ungültige Anfrage."}, status=400)

    valid_units = {u[0] for u in UnitChoices.choices}
    added_count = 0

    for raw_item in items:
        ingredient_id = raw_item.get("ingredient_id")
        if not ingredient_id:
            continue

        try:
            ingredient = Ingredient.objects.get(pk=ingredient_id)
        except (Ingredient.DoesNotExist, ValueError, TypeError):
            continue

        unit = raw_item.get("unit") or "pcs"
        if unit not in valid_units:
            unit = "pcs"

        try:
            qty = Decimal(str(raw_item.get("quantity") or "1"))
        except Exception:
            qty = Decimal("1")

        item, created = InventoryItem.objects.get_or_create(
            household=household,
            ingredient=ingredient,
            defaults={"quantity": qty, "unit": unit},
        )

        if not created:
            item.quantity = (item.quantity or Decimal("0")) + qty
            item.unit = item.unit or unit
            item.save()

        added_count += 1

    return JsonResponse({"success": True, "added": added_count})


@login_required
@require_POST
def barcode_remove(request, item_id):
    """Subtract scanned quantity from inventory item, delete if depleted."""
    import json
    from decimal import Decimal
    from shopping.utils import to_base_unit

    data = json.loads(request.body)
    household = request.user.households.first()
    item = get_object_or_404(InventoryItem, pk=item_id, household=household)

    subtract_qty = data.get("subtract_quantity")
    subtract_unit = data.get("subtract_unit") or item.unit

    # If no quantity tracked in inventory, just delete
    if item.quantity is None:
        item.delete()
        return JsonResponse({"success": True, "deleted": True})

    try:
        sub_qty = Decimal(str(subtract_qty)) if subtract_qty else item.quantity
    except Exception:
        sub_qty = item.quantity

    # Convert to same base unit for subtraction
    inv_base, inv_unit = to_base_unit(item.quantity, item.unit)
    sub_base, sub_unit_base = to_base_unit(sub_qty, subtract_unit)

    if inv_unit == sub_unit_base:
        remaining_base = inv_base - sub_base
    else:
        # Incompatible units — just delete
        item.delete()
        return JsonResponse({"success": True, "deleted": True})

    if remaining_base <= 0:
        item.delete()
        return JsonResponse({"success": True, "deleted": True})

    # Convert back
    from shopping.utils import from_base_unit
    remaining_qty, remaining_unit = from_base_unit(remaining_base, inv_unit)
    item.quantity = remaining_qty
    item.unit = remaining_unit
    item.save()

    return JsonResponse({
        "success": True,
        "deleted": False,
        "remaining": str(remaining_qty.normalize()),
        "unit": remaining_unit,
    })