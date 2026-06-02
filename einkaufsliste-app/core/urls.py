from django.urls import path
from .views import home, barcode_lookup

urlpatterns = [
    path("", home, name="home"),
    path("api/barcode/", barcode_lookup, name="barcode_lookup"),
]