from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import InventoryItem, Unit
from recipes.models import Recipe
from .forms import ShoppingListItemForm
from .models import ShoppingList, ShoppingListItem
from .utils import to_base_unit, from_base_unit


def shopping_list(request):
    recipe_ids = request.GET.getlist("recipes")

    shopping_list_obj = _get_or_create_active_shopping_list()

    if recipe_ids:
        servings_map = {}

        for recipe_id in recipe_ids:
            servings_value = request.GET.get(f"servings_{recipe_id}")
            if servings_value:
                try:
                    servings_map[int(recipe_id)] = int(servings_value)
                except ValueError:
                    pass

        _add_recipes_to_existing_shopping_list(shopping_list_obj, recipe_ids, servings_map)
        return redirect("shopping:detail", pk=shopping_list_obj.pk)

    return redirect("shopping:detail", pk=shopping_list_obj.pk)


def shopping_list_detail(request, pk):
    shopping_list_obj = get_object_or_404(
        ShoppingList.objects.prefetch_related("items__ingredient"),
        pk=pk,
    )

    create_form = ShoppingListItemForm()
    create_modal_open = False

    if request.method == "POST":
        action = request.POST.get("action")
        checked_ids = request.POST.getlist("checked_items")

        if action == "create":
            create_form = ShoppingListItemForm(request.POST)
            if create_form.is_valid():
                _add_manual_item_to_shopping_list(shopping_list_obj, create_form)
                messages.success(request, "Lebensmittel wurde zur Einkaufsliste hinzugefügt.")
                return redirect("shopping:detail", pk=shopping_list_obj.pk)
            create_modal_open = True

        elif action == "delete_selected":
            if checked_ids:
                deleted_count = shopping_list_obj.items.filter(id__in=checked_ids).count()
                shopping_list_obj.items.filter(id__in=checked_ids).delete()
                messages.success(request, f"{deleted_count} Einträge wurden gelöscht.")
            return redirect("shopping:detail", pk=shopping_list_obj.pk)

        elif action == "clean":
            shopping_list_obj.items.update(is_checked=False)
            if checked_ids:
                shopping_list_obj.items.filter(id__in=checked_ids).update(is_checked=True)

            checked_items = shopping_list_obj.items.filter(is_checked=True)
            count = checked_items.count()

            _move_checked_items_to_inventory(checked_items)
            checked_items.delete()

            if count > 0:
                messages.success(request, f"{count} Einträge wurden ins Inventar übernommen.")

            return redirect("shopping:detail", pk=shopping_list_obj.pk)

    to_buy = shopping_list_obj.items.filter(status=ShoppingListItem.STATUS_TO_BUY)
    check_quantity = shopping_list_obj.items.filter(status=ShoppingListItem.STATUS_CHECK)

    return render(request, "shopping/shopping_list.html", {
        "shopping_list_obj": shopping_list_obj,
        "to_buy": to_buy,
        "check_quantity": check_quantity,
        "create_form": create_form,
        "create_modal_open": create_modal_open,
    })


def _get_or_create_active_shopping_list():
    shopping_list_obj = ShoppingList.objects.first()
    if not shopping_list_obj:
        shopping_list_obj = ShoppingList.objects.create()
    return shopping_list_obj


def _add_recipes_to_existing_shopping_list(shopping_list_obj, recipe_ids, servings_map=None):
    recipes = Recipe.objects.filter(id__in=recipe_ids).prefetch_related(
        "recipe_ingredients__ingredient"
    )

    servings_map = servings_map or {}
    aggregated_items = defaultdict(list)

    for recipe in recipes:
        target_servings = servings_map.get(recipe.id, recipe.servings)
        factor = recipe.scale_factor(target_servings)

        for item in recipe.recipe_ingredients.all():
            scaled_quantity = item.quantity * factor
            base_quantity, base_unit = to_base_unit(scaled_quantity, item.unit)
            key = (item.ingredient_id, base_unit)

            aggregated_items[key].append({
                "recipe_id": recipe.id,
                "recipe_name": recipe.name,
                "quantity": base_quantity,
                "unit": base_unit,
            })

    inventory_items = {
        item.ingredient_id: item
        for item in InventoryItem.objects.select_related("ingredient")
    }

    for (ingredient_id, base_unit), source_entries in aggregated_items.items():
        required_base_quantity = sum(entry["quantity"] for entry in source_entries)
        inventory_item = inventory_items.get(ingredient_id)

        normalized_source_details = []
        for entry in source_entries:
            display_quantity, display_unit = from_base_unit(entry["quantity"], entry["unit"])
            normalized_source_details.append({
                "recipe_id": entry["recipe_id"],
                "recipe_name": entry["recipe_name"],
                "quantity": str(display_quantity),
                "unit": display_unit,
            })

        if not inventory_item:
            quantity, unit = from_base_unit(required_base_quantity, base_unit)
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_TO_BUY,
                source_details=normalized_source_details,
            )
            continue

        if inventory_item.quantity is None:
            quantity, unit = from_base_unit(required_base_quantity, base_unit)
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_CHECK,
                source_details=normalized_source_details,
            )
            continue

        inventory_base_quantity, inventory_base_unit = to_base_unit(
            inventory_item.quantity,
            inventory_item.unit,
        )

        if inventory_base_unit != base_unit:
            quantity, unit = from_base_unit(required_base_quantity, base_unit)
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_CHECK,
                source_details=normalized_source_details,
            )
            continue

        if inventory_base_quantity >= required_base_quantity:
            continue

        missing_base_quantity = required_base_quantity - inventory_base_quantity
        quantity, unit = from_base_unit(missing_base_quantity, base_unit)

        _merge_or_create_shopping_item(
            shopping_list_obj=shopping_list_obj,
            ingredient_id=ingredient_id,
            quantity=quantity,
            unit=unit,
            status=ShoppingListItem.STATUS_TO_BUY,
            source_details=normalized_source_details,
        )

def _merge_or_create_shopping_item(
    shopping_list_obj,
    ingredient_id,
    quantity,
    unit,
    status,
    source_details=None,
):
    source_details = source_details or []
    base_quantity, base_unit = to_base_unit(quantity, unit)

    existing_items = shopping_list_obj.items.filter(
        ingredient_id=ingredient_id,
        status=status,
    )

    for existing_item in existing_items:
        existing_base_quantity, existing_base_unit = to_base_unit(
            existing_item.quantity,
            existing_item.unit,
        )

        if existing_base_unit == base_unit:
            if existing_base_quantity is not None and base_quantity is not None:
                total_base_quantity = existing_base_quantity + base_quantity
                new_quantity, new_unit = from_base_unit(total_base_quantity, base_unit)

                existing_item.quantity = new_quantity
                existing_item.unit = new_unit
                existing_item.source_details = _merge_source_details(
                    existing_item.source_details or [],
                    source_details,
                )
                existing_item.save(update_fields=["quantity", "unit", "source_details"])
                return

            existing_item.source_details = _merge_source_details(
                existing_item.source_details or [],
                source_details,
            )
            existing_item.save(update_fields=["source_details"])
            return

    ShoppingListItem.objects.create(
        shopping_list=shopping_list_obj,
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit=unit,
        status=status,
        source_details=source_details,
    )


def _add_manual_item_to_shopping_list(shopping_list_obj, form):
    ingredient = form.cleaned_data["ingredient"]
    quantity = form.cleaned_data["quantity"]
    unit = form.cleaned_data["unit"]

    status = (
        ShoppingListItem.STATUS_CHECK
        if quantity is None
        else ShoppingListItem.STATUS_TO_BUY
    )

    if quantity is None:
        existing_item = shopping_list_obj.items.filter(
            ingredient=ingredient,
            status=status,
            quantity__isnull=True,
        ).first()

        if existing_item:
            return

        ShoppingListItem.objects.create(
            shopping_list=shopping_list_obj,
            ingredient=ingredient,
            quantity=None,
            unit="",
            status=status,
            source_details=[],
        )
        return

    _merge_or_create_shopping_item(
        shopping_list_obj=shopping_list_obj,
        ingredient_id=ingredient.id,
        quantity=quantity,
        unit=unit,
        status=status,
        source_details=[],
    )


def _move_checked_items_to_inventory(checked_items):
    for item in checked_items.select_related("ingredient"):
        inventory_item = InventoryItem.objects.filter(ingredient=item.ingredient).first()

        # TL / EL nie als exakte Lagermenge speichern
        if item.unit in [Unit.TABLESPOON, Unit.TEASPOON]:
            if not inventory_item:
                InventoryItem.objects.create(
                    ingredient=item.ingredient,
                    quantity=None,
                    unit="",
                )
            continue

        item_base_quantity, item_base_unit = to_base_unit(item.quantity, item.unit)

        if not inventory_item:
            if item.quantity is None:
                InventoryItem.objects.create(
                    ingredient=item.ingredient,
                    quantity=None,
                    unit="",
                )
            else:
                display_quantity, display_unit = from_base_unit(item_base_quantity, item_base_unit)
                InventoryItem.objects.create(
                    ingredient=item.ingredient,
                    quantity=display_quantity,
                    unit=display_unit,
                )
            continue

        if inventory_item.quantity is None:
            continue

        if item.quantity is None:
            continue

        inventory_base_quantity, inventory_base_unit = to_base_unit(
            inventory_item.quantity,
            inventory_item.unit,
        )

        if inventory_base_unit != item_base_unit:
            continue

        total_base_quantity = inventory_base_quantity + item_base_quantity
        display_quantity, display_unit = from_base_unit(total_base_quantity, inventory_base_unit)

        inventory_item.quantity = display_quantity
        inventory_item.unit = display_unit
        inventory_item.save(update_fields=["quantity", "unit", "updated_at"])


def _merge_source_details(existing_sources, new_sources):
    merged = list(existing_sources)

    for new_source in new_sources:
        match = next(
            (
                item for item in merged
                if item.get("recipe_id") == new_source.get("recipe_id")
                and item.get("unit") == new_source.get("unit")
            ),
            None,
        )

        if match:
            try:
                existing_quantity = Decimal(str(match.get("quantity", "0")))
                new_quantity = Decimal(str(new_source.get("quantity", "0")))
                total_quantity = existing_quantity + new_quantity
                match["quantity"] = str(total_quantity)
            except Exception:
                pass
        else:
            merged.append(new_source)

    return merged