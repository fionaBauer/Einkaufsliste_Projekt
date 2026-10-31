from django.urls import path
from .views import home, barcode_lookup, service_worker

urlpatterns = [
    path("", home, name="home"),
    path("sw.js", service_worker, name="service_worker"),
    path("api/barcode/", barcode_lookup, name="barcode_lookup"),
]