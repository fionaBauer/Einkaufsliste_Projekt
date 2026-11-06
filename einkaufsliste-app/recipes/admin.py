from django.contrib import admin
from .models import Recipe, RecipeIngredient, RecipeTag


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeTagInline(admin.TabularInline):
    model = RecipeTag
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "servings", "created_at")
    search_fields = ("name",)
    inlines = [RecipeIngredientInline, RecipeTagInline]


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "quantity", "unit", "notes")
    list_filter = ("unit", "recipe")
    search_fields = ("recipe__name", "ingredient__name")