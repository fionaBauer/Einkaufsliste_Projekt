from django.urls import path
from .views import inventory_list

app_name = "inventory"

urlpatterns = [
    path("", inventory_list, name="list"),
]