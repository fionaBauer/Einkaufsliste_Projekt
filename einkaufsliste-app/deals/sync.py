from deals.models import DealSource, Store, Deal
from deals.providers.marktguru import MarktguruProvider
from deals.services import SYNONYMS
from ingredients.models import Ingredient


COMMON_PRODUCTS = [
    "nudeln", "pasta", "spaghetti", "penne",
    "reis", "kartoffeln",
    "tomaten", "gurke", "paprika",
    "salat", "zwiebeln", "knoblauch",
    "milch", "joghurt", "käse", "mozzarella",
    "hackfleisch", "hähnchen",
    "brot", "toast", "eier",
]


def build_search_terms():
    terms = set()

    for ingredient in Ingredient.objects.values_list("name", flat=True):
        if ingredient:
            terms.add(ingredient.lower().strip())

    for key, values in SYNONYMS.items():
        terms.add(key.lower().strip())

        for value in values:
            terms.add(value.lower().strip())

    for product in COMMON_PRODUCTS:
        terms.add(product.lower().strip())

    return sorted(term for term in terms if len(term) >= 3)


def sync_marktguru(zip_code, limit=50):
    provider = MarktguruProvider(zip_code=zip_code)

    source, _ = DealSource.objects.get_or_create(
        name=provider.source_name,
        defaults={"base_url": "https://www.marktguru.de"},
    )

    Deal.objects.filter(source=source).delete()

    imported_deals = provider.fetch_deals(
        search_terms=build_search_terms(),
        limit=limit,
    )

    saved_count = 0

    for imported in imported_deals:
        store, _ = Store.objects.get_or_create(
            name=imported.store_name,
            defaults={
                "location": "",
                "postal_code": zip_code,
            },
        )

        Deal.objects.update_or_create(
            source=source,
            external_id=imported.external_id,
            defaults={
                "store": store,
                "title": imported.title,
                "description": imported.description,
                "original_price": imported.original_price,
                "deal_price": imported.deal_price,
                "discount_text": imported.discount_text,
                "product_url": imported.product_url,
                "image_url": imported.image_url,
                "valid_from": imported.valid_from,
                "valid_until": imported.valid_until,
            },
        )

        saved_count += 1

    return saved_count