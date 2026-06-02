from django.urls import path
from .views import shopping_list, shopping_list_detail, barcode_add

app_name = "shopping"

urlpatterns = [
    path("", shopping_list, name="list"),
    path("<int:pk>/", shopping_list_detail, name="detail"),
    path("barcode-add/", barcode_add, name="barcode_add"),
]