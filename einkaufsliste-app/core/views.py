from django.shortcuts import render
from recipes.models import Recipe


def home(request):
    recent_recipes = Recipe.objects.order_by("-created_at")[:5]

    context = {
        "recent_recipes": recent_recipes,
    }
    return render(request, "core/home.html", context)