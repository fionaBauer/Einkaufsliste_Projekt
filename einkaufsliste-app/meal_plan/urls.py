from django.urls import path
from . import views

app_name = "meal_plan"

urlpatterns = [
    path("", views.planner, name="planner"),
    path("api/slots/", views.slots_api, name="slots_api"),
    path("api/slots/create/", views.slot_create, name="slot_create"),
    path("api/slots/<int:pk>/", views.slot_update, name="slot_update"),
    path("api/slots/<int:pk>/delete/", views.slot_delete, name="slot_delete"),
    path("api/shopping-list/", views.create_shopping_list, name="create_shopping_list"),
]