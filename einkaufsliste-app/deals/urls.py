from django.urls import path
from . import views

app_name = "deals"

urlpatterns = [
    path("sync/", views.sync_deals_view, name="sync"),
]
