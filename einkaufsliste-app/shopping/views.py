from collections import defaultdict
from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect, render

from inventory.models import InventoryItem
from recipes.models import Recipe
from .models import ShoppingList, ShoppingListItem


def shopping_list(request):
    recipe_ids = request.GET.getlist("recipes")

    if recipe_ids:
        shopping_list_obj = _create_or_replace_shopping_list(recipe_ids)
        return redirect("shopping:detail", pk=shopping_list_obj.pk)

    latest_list = ShoppingList.objects.first()
    if latest_list:
        return redirect("shopping:detail", pk=latest_list.pk)

    return render(request, "shopping/shopping_list.html", {
        "shopping_list_obj": None,
        "to_buy": [],
        "already_have": [],
        "check_quantity": [],
    })


def shopping_list_detail(request, pk):
    shopping_list_obj = get_object_or_404(
        ShoppingList.objects.prefetch_related("items__ingredient"),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        checked_ids = request.POST.getlist("checked_items")

        if action == "reset":
            checked_items = shopping_list_obj.items.filter(id__in=checked_ids)
            _move_checked_items_to_inventory(checked_items)

            shopping_list_obj.items.update(is_checked=False)
            return redirect("shopping:detail", pk=shopping_list_obj.pk)

        if action == "clean":
            shopping_list_obj.items.update(is_checked=False)
            if checked_ids:
                shopping_list_obj.items.filter(id__in=checked_ids).update(is_checked=True)

            checked_items = shopping_list_obj.items.filter(is_checked=True)
            _move_checked_items_to_inventory(checked_items)

            checked_items.delete()
            return redirect("shopping:detail", pk=shopping_list_obj.pk)

    to_buy = shopping_list_obj.items.filter(status=ShoppingListItem.STATUS_TO_BUY)
    already_have = shopping_list_obj.items.filter(status=ShoppingListItem.STATUS_HAVE)
    check_quantity = shopping_list_obj.items.filter(status=ShoppingListItem.STATUS_CHECK)

    return render(request, "shopping/shopping_list.html", {
        "shopping_list_obj": shopping_list_obj,
        "to_buy": to_buy,
        "already_have": already_have,
        "check_quantity": check_quantity,
    })


def _create_or_replace_shopping_list(recipe_ids):
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

    ShoppingList.objects.all().delete()
    shopping_list_obj = ShoppingList.objects.create()

    items_to_create = []

    for (ingredient_id, unit), required_quantity in aggregated_items.items():
        inventory_item = inventory_items.get(ingredient_id)

        if not inventory_item:
            items_to_create.append(
                ShoppingListItem(
                    shopping_list=shopping_list_obj,
                    ingredient_id=ingredient_id,
                    quantity=required_quantity,
                    unit=unit,
                    status=ShoppingListItem.STATUS_TO_BUY,
                )
            )
            continue

        if inventory_item.quantity is None:
            items_to_create.append(
                ShoppingListItem(
                    shopping_list=shopping_list_obj,
                    ingredient_id=ingredient_id,
                    quantity=required_quantity,
                    unit=unit,
                    status=ShoppingListItem.STATUS_CHECK,
                )
            )
            continue

        if inventory_item.unit != unit:
            items_to_create.append(
                ShoppingListItem(
                    shopping_list=shopping_list_obj,
                    ingredient_id=ingredient_id,
                    quantity=required_quantity,
                    unit=unit,
                    status=ShoppingListItem.STATUS_CHECK,
                )
            )
            continue

        inventory_quantity = inventory_item.quantity

        if inventory_quantity >= required_quantity:
            items_to_create.append(
                ShoppingListItem(
                    shopping_list=shopping_list_obj,
                    ingredient_id=ingredient_id,
                    quantity=required_quantity,
                    unit=unit,
                    status=ShoppingListItem.STATUS_HAVE,
                )
            )
        else:
            missing_quantity = required_quantity - inventory_quantity
            items_to_create.append(
                ShoppingListItem(
                    shopping_list=shopping_list_obj,
                    ingredient_id=ingredient_id,
                    quantity=missing_quantity,
                    unit=unit,
                    status=ShoppingListItem.STATUS_TO_BUY,
                )
            )

    ShoppingListItem.objects.bulk_create(items_to_create)
    return shopping_list_obj


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