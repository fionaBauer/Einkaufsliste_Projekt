from collections import OrderedDict

from django.shortcuts import get_object_or_404, redirect, render

from ingredients.models import IngredientCategory
from .forms import InventoryItemForm
from .models import InventoryItem


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
        "sort_options": [
            ("name_asc", "Name A–Z"),
            ("name_desc", "Name Z–A"),
            ("quantity_asc", "Menge aufsteigend"),
            ("quantity_desc", "Menge absteigend"),
        ],
    }
    return render(request, "inventory/inventory_list.html", context)