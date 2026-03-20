from django.urls import path
from .views import ingredient_list

app_name = "ingredients"

urlpatterns = [
    path("", ingredient_list, name="list"),
]