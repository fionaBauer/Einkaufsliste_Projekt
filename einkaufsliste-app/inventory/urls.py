from django.urls import path
from .views import inventory_list, recipe_consume_preview, apply_recipe_consumption

app_name = "inventory"

urlpatterns = [
    path("", inventory_list, name="list"),
    path("consume-recipe-preview/", recipe_consume_preview, name="consume_recipe_preview"),
    path("apply-recipe-consumption/", apply_recipe_consumption, name="apply_recipe_consumption"),
]