from django.urls import path
from .views import ingredient_list, ingredient_create_modal, ingredient_api_list, ingredient_guess_category

app_name = "ingredients"

urlpatterns = [
    path("", ingredient_list, name="list"),
    path("modal/create/", ingredient_create_modal, name="modal_create"),
    path("api/list/", ingredient_api_list, name="api_list"),
    path("api/guess-category/", ingredient_guess_category, name="api_guess_category"),
]