from django.urls import path
from .views import ingredient_list, ingredient_create_modal

app_name = "ingredients"

urlpatterns = [
    path("", ingredient_list, name="list"),
    path("modal/create/", ingredient_create_modal, name="modal_create"),
]