from django.urls import path
from . import views

app_name = "households"

urlpatterns = [
    path("create/", views.household_create, name="create"),
    path("", views.household_detail, name="detail"),
    path("join/<uuid:token>/", views.household_join, name="join"),
]
