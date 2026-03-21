from django.urls import path
from .views import shopping_list

app_name = "shopping"

urlpatterns = [
    path("", shopping_list, name="list"),
]