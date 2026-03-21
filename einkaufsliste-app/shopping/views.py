from collections import defaultdict
from django.shortcuts import render
from recipes.models import Recipe


def shopping_list(request):
    recipe_ids = request.GET.getlist("recipes")

    recipes = Recipe.objects.filter(id__in=recipe_ids).prefetch_related("recipe_ingredients__ingredient")

    shopping_dict = defaultdict(float)

    for recipe in recipes:
        for item in recipe.recipe_ingredients.all():
            key = (item.ingredient.name, item.unit)
            shopping_dict[key] += float(item.quantity)

    shopping_list = [
        {
            "name": name,
            "unit": unit,
            "quantity": quantity,
        }
        for (name, unit), quantity in shopping_dict.items()
    ]

    shopping_list.sort(key=lambda x: x["name"])

    return render(request, "shopping/shopping_list.html", {
        "shopping_list": shopping_list,
        "recipes": recipes,
    })