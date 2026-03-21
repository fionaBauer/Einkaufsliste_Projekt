from django.urls import path
from .views import shopping_list, shopping_list_detail

app_name = "shopping"

urlpatterns = [
    path("", shopping_list, name="list"),
    path("<int:pk>/", shopping_list_detail, name="detail"),
]