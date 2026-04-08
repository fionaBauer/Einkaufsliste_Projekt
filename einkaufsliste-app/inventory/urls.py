from django.urls import path
from .views import inventory_list, recipe_consume_preview

app_name = "inventory"

urlpatterns = [
    path("", inventory_list, name="list"),
    path("consume-recipe-preview/", recipe_consume_preview, name="consume_recipe_preview"),
]