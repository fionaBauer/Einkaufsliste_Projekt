from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from .forms import IngredientForm
from .categories import CATEGORY_ICONS
from .models import Ingredient, IngredientCategory


def _build_grouped_ingredients(search_query, sort):
    ingredients = Ingredient.objects.all()

    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    if sort == "name_desc":
        ingredients = ingredients.order_by("-name")
    else:
        ingredients = ingredients.order_by("name")

    grouped = []

    for category_value, category_label in IngredientCategory.choices:
        category_items = [ingredient for ingredient in ingredients if ingredient.category == category_value]
        if category_items:
            grouped.append({
                "value": category_value,
                "label": category_label,
                "icon": CATEGORY_ICONS.get(category_value, "📦"),
                "items": category_items,
            })

    return grouped


def _render_ingredient_list_section(request, search_query, sort):
    return render_to_string(
        "ingredients/partials/ingredient_list_section.html",
        {
            "grouped_ingredients": _build_grouped_ingredients(search_query, sort),
            "search_query": search_query,
        },
        request=request,
    )


@login_required
def ingredient_list(request):
    search_query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name_asc")

    grouped_ingredients = _build_grouped_ingredients(search_query, sort)

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
                return redirect(request.get_full_path())
            create_modal_open = True

        elif action == "edit":
            ingredient_id = request.POST.get("ingredient_id")
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
            edit_form = IngredientForm(request.POST, instance=ingredient)
            edit_ingredient_id = ingredient.id

            if edit_form.is_valid():
                edit_form.save()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    section_html = _render_ingredient_list_section(request, search_query, sort)
                    return JsonResponse({"success": True, "section_html": section_html})
                return redirect(request.get_full_path())

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": edit_form.errors}, status=400)
            edit_modal_open = True

        elif action == "delete":
            ingredient_id = request.POST.get("ingredient_id")
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
            ingredient.delete()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                section_html = _render_ingredient_list_section(request, search_query, sort)
                return JsonResponse({"success": True, "section_html": section_html})
            return redirect(request.get_full_path())

    if edit_form is None:
        edit_form = IngredientForm()

    context = {
        "grouped_ingredients": grouped_ingredients,
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
        ],
    }
    return render(request, "ingredients/ingredient_list.html", context)

@login_required
@require_http_methods(["GET", "POST"])
def ingredient_create_modal(request):
    if request.method == "GET":
        form = IngredientForm()
        html = render_to_string(
            "ingredients/partials/ingredient_form.html",
            {"form": form},
            request=request,
        )
        return JsonResponse({"html": html})

    form = IngredientForm(request.POST)

    if form.is_valid():
        ingredient = form.save()
        return JsonResponse({
            "success": True,
            "ingredient": {
                "id": ingredient.id,
                "name": ingredient.name,
                "default_unit": ingredient.default_unit,
                "default_unit_display": ingredient.get_default_unit_display(),
            }
        })

    html = render_to_string(
        "ingredients/partials/ingredient_form.html",
        {"form": form},
        request=request,
    )
    return JsonResponse({"success": False, "html": html})

from django.http import JsonResponse as _JsonResponse
from django.contrib.auth.decorators import login_required as _login_required

@_login_required
def ingredient_api_list(request):
    """Returns all ingredients as JSON for autocomplete."""
    ingredients = Ingredient.objects.values("id", "name", "default_unit").order_by("name")
    return _JsonResponse(list(ingredients), safe=False)

@_login_required
def ingredient_guess_category(request):
    """Kategorie-Vorschlag beim Anlegen einer Zutat (während des Tippens)."""
    from .categories import guess_category

    return _JsonResponse({"category": guess_category(request.GET.get("name", ""))})
