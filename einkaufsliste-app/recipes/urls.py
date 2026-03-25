from django.urls import path
from .views import (
    RecipeListView,
    RecipeDetailView,
    RecipeCreateView,
    RecipeUpdateView,
    RecipeDeleteView,
    RecipeIngredientCreateView,
    RecipeIngredientUpdateView,
    RecipeIngredientDeleteView,
    extract_recipe_from_link,
    create_recipe_from_extracted_data,
    ffmpeg_debug
)

app_name = "recipes"

urlpatterns = [
    path("", RecipeListView.as_view(), name="recipe_list"),
    path("<int:pk>/", RecipeDetailView.as_view(), name="recipe_detail"),

    path("create/", RecipeCreateView.as_view(), name="recipe_create"),
    path("<int:pk>/edit/", RecipeUpdateView.as_view(), name="recipe_edit"),
    path("<int:pk>/delete/", RecipeDeleteView.as_view(), name="recipe_delete"),

    path("<int:recipe_pk>/ingredients/create/", RecipeIngredientCreateView.as_view(), name="recipeingredient_create"),
    path("ingredients/<int:pk>/edit/", RecipeIngredientUpdateView.as_view(), name="recipeingredient_edit"),
    path("ingredients/<int:pk>/delete/", RecipeIngredientDeleteView.as_view(), name="recipeingredient_delete"),

    path("extract-from-link/", extract_recipe_from_link, name="recipe_extract_from_link"),
    path("create-from-extracted/", create_recipe_from_extracted_data, name="recipe_create_from_extracted"),

    path("ffmpeg-debug/", ffmpeg_debug, name="ffmpeg_debug"),
]