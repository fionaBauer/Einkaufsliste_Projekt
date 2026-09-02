from django.urls import path
from .views import (
    inventory_list,
    recipe_consume_preview,
    apply_recipe_consumption,
    barcode_add,
    barcode_remove,
    receipt_scan,
    receipt_confirm,
)

app_name = "inventory"

urlpatterns = [
    path("", inventory_list, name="list"),
    path("consume-recipe-preview/", recipe_consume_preview, name="consume_recipe_preview"),
    path("apply-recipe-consumption/", apply_recipe_consumption, name="apply_recipe_consumption"),
    path("barcode-add/", barcode_add, name="barcode_add"),
    path("barcode-remove/<int:item_id>/", barcode_remove, name="barcode_remove"),
    path("receipt-scan/", receipt_scan, name="receipt_scan"),
    path("receipt-confirm/", receipt_confirm, name="receipt_confirm"),
]