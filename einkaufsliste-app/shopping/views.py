from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import InventoryItem
from recipes.models import Recipe
from .forms import ShoppingListItemForm
from .models import ShoppingList, ShoppingListItem


def shopping_list(request):
    recipe_ids = request.GET.getlist("recipes")

    shopping_list_obj = _get_or_create_active_shopping_list()

    if recipe_ids:
        _add_recipes_to_existing_shopping_list(shopping_list_obj, recipe_ids)
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


def _add_recipes_to_existing_shopping_list(shopping_list_obj, recipe_ids):
    recipes = Recipe.objects.filter(id__in=recipe_ids).prefetch_related(
        "recipe_ingredients__ingredient"
    )

    aggregated_items = defaultdict(Decimal)

    for recipe in recipes:
        for item in recipe.recipe_ingredients.all():
            key = (item.ingredient_id, item.unit)
            aggregated_items[key] += item.quantity

    inventory_items = {
        item.ingredient_id: item
        for item in InventoryItem.objects.select_related("ingredient")
    }

    for (ingredient_id, unit), required_quantity in aggregated_items.items():
        inventory_item = inventory_items.get(ingredient_id)

        if not inventory_item:
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=required_quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_TO_BUY,
            )
            continue

        if inventory_item.quantity is None:
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=required_quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_CHECK,
            )
            continue

        if inventory_item.unit != unit:
            _merge_or_create_shopping_item(
                shopping_list_obj=shopping_list_obj,
                ingredient_id=ingredient_id,
                quantity=required_quantity,
                unit=unit,
                status=ShoppingListItem.STATUS_CHECK,
            )
            continue

        inventory_quantity = inventory_item.quantity

        if inventory_quantity >= required_quantity:
            continue

        missing_quantity = required_quantity - inventory_quantity
        _merge_or_create_shopping_item(
            shopping_list_obj=shopping_list_obj,
            ingredient_id=ingredient_id,
            quantity=missing_quantity,
            unit=unit,
            status=ShoppingListItem.STATUS_TO_BUY,
        )


def _merge_or_create_shopping_item(shopping_list_obj, ingredient_id, quantity, unit, status):
    existing_item = shopping_list_obj.items.filter(
        ingredient_id=ingredient_id,
        unit=unit,
        status=status,
    ).first()

    if existing_item:
        if existing_item.quantity is not None and quantity is not None:
            existing_item.quantity += quantity
            existing_item.save(update_fields=["quantity"])
        return

    ShoppingListItem.objects.create(
        shopping_list=shopping_list_obj,
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit=unit,
        status=status,
    )


def _add_manual_item_to_shopping_list(shopping_list_obj, form):
    ingredient = form.cleaned_data["ingredient"]
    quantity = form.cleaned_data["quantity"]
    unit = form.cleaned_data["unit"]

    status = ShoppingListItem.STATUS_CHECK if quantity is None else ShoppingListItem.STATUS_TO_BUY

    existing_item = shopping_list_obj.items.filter(
        ingredient=ingredient,
        unit=unit,
        status=status,
    ).first()

    if existing_item and existing_item.quantity is not None and quantity is not None:
        existing_item.quantity += quantity
        existing_item.save(update_fields=["quantity"])
        return

    if existing_item and quantity is None:
        return

    ShoppingListItem.objects.create(
        shopping_list=shopping_list_obj,
        ingredient=ingredient,
        quantity=quantity,
        unit=unit,
        status=status,
    )


def _move_checked_items_to_inventory(checked_items):
    for item in checked_items.select_related("ingredient"):
        inventory_item = InventoryItem.objects.filter(ingredient=item.ingredient).first()

        if not inventory_item:
            InventoryItem.objects.create(
                ingredient=item.ingredient,
                quantity=item.quantity if item.quantity is not None else None,
                unit=item.unit if item.quantity is not None else "",
            )
            continue

        if inventory_item.quantity is None:
            continue

        if item.quantity is None:
            continue

        if inventory_item.unit != item.unit:
            continue

        inventory_item.quantity += item.quantity
        inventory_item.save(update_fields=["quantity", "updated_at"])