from django.contrib import admin
from .models import DealSource, Store, Deal


@admin.register(DealSource)
class DealSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "base_url", "is_active")
    search_fields = ("name",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "postal_code")
    search_fields = ("name", "location", "postal_code")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "store",
        "deal_price",
        "original_price",
        "discount_text",
        "matched_ingredient",
        "valid_until",
    )
    list_filter = ("store", "source", "valid_until")
    search_fields = ("title", "description", "store__name", "matched_ingredient__name")
    autocomplete_fields = ("matched_ingredient",)   