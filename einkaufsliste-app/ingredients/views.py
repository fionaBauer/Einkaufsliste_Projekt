from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render

from .forms import IngredientForm
from .models import Ingredient


def ingredient_list(request):
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name_asc")

    ingredients = Ingredient.objects.all()

    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    if sort == "name_desc":
        ingredients = ingredients.order_by("-name")
    elif sort == "unit_asc":
        ingredients = ingredients.order_by("default_unit", "name")
    elif sort == "unit_desc":
        ingredients = ingredients.order_by("-default_unit", "name")
    else:
        ingredients = ingredients.order_by("name")

    create_form = IngredientForm()
    edit_form = None
    edit_ingredient_id = None
    create_modal_open = False
    edit_modal_open = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            create_form = IngredientForm(request.POST)
            if create_form.is_valid():
                create_form.save()
                return redirect("ingredients:list")
            create_modal_open = True

        elif action == "edit":
            ingredient_id = request.POST.get("ingredient_id")
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
            edit_form = IngredientForm(request.POST, instance=ingredient)
            edit_ingredient_id = ingredient.id

            if edit_form.is_valid():
                edit_form.save()
                return redirect("ingredients:list")
            edit_modal_open = True

        elif action == "delete":
            ingredient_id = request.POST.get("ingredient_id")
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
            ingredient.delete()
            return redirect("ingredients:list")

    if edit_form is None:
        edit_form = IngredientForm()

    context = {
        "ingredients": ingredients,
        "create_form": create_form,
        "edit_form": edit_form,
        "edit_ingredient_id": edit_ingredient_id,
        "create_modal_open": create_modal_open,
        "edit_modal_open": edit_modal_open,
        "search_query": search_query,
        "sort": sort,
        "sort_options": [
            ("name_asc", "Name A–Z"),
            ("name_desc", "Name Z–A"),
            ("unit_asc", "Einheit A–Z"),
            ("unit_desc", "Einheit Z–A"),
        ],
    }
    return render(request, "ingredients/ingredient_list.html", context)