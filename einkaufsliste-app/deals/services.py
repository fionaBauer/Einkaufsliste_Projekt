from decimal import Decimal
from django.db.models import Q
from django.utils import timezone

from .models import Deal


SYNONYMS = {
    "nudeln": ["pasta", "spaghetti", "penne", "fusilli", "tagliatelle"],
    "pasta": ["nudeln", "spaghetti", "penne", "fusilli", "tagliatelle"],
    "tomate": ["tomaten", "roma tomaten", "cherrytomaten"],
    "tomaten": ["tomate", "roma tomaten", "cherrytomaten"],
    "hackfleisch": ["hack", "rinderhack", "gemischtes hackfleisch"],
    "gurke": ["salatgurke"],
}


def get_active_deals():
    today = timezone.now().date()

    return Deal.objects.select_related("store", "source").filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )


def get_search_terms(ingredient_name):
    name = ingredient_name.lower().strip()
    words = [
        word.strip()
        for word in name.replace("-", " ").split()
        if len(word.strip()) >= 3
    ]

    terms = set([name, *words])

    for term in list(terms):
        terms.update(SYNONYMS.get(term, []))

    return terms


def find_deals_for_ingredient(ingredient, active_deals=None):
    """
    active_deals: optional pre-fetched iterable of Deal objects (list or queryset,
    e.g. from get_active_deals()). Pass this in when matching many ingredients in a
    loop to avoid firing one DB query per ingredient (N+1) - see
    attach_deals_to_shopping_items / get_suggested_recipes_by_deals below.
    """
    deals = active_deals if active_deals is not None else get_active_deals()
    terms = get_search_terms(ingredient.name)

    matched = [
        deal for deal in deals
        if any(term in deal.title.lower() for term in terms)
    ]
    matched.sort(key=lambda deal: (deal.deal_price is None, deal.deal_price, deal.store.name))
    return matched


def attach_deals_to_shopping_items(items, active_deals=None):
    deals = active_deals if active_deals is not None else list(get_active_deals())
    for item in items:
        item.discount_deals = find_deals_for_ingredient(item.ingredient, deals)[:3]
    return items


def calculate_store_savings(items):
    savings_by_store = {}

    for item in items:
        for deal in getattr(item, "discount_deals", []):
            if deal.savings is None:
                continue

            store_name = deal.store.name

            if store_name not in savings_by_store:
                savings_by_store[store_name] = {
                    "store": deal.store,
                    "total_savings": Decimal("0.00"),
                    "deals": [],
                }

            savings_by_store[store_name]["total_savings"] += deal.savings
            savings_by_store[store_name]["deals"].append({
                "item": item,
                "deal": deal,
                "savings": deal.savings,
            })

    return sorted(
        savings_by_store.values(),
        key=lambda entry: entry["total_savings"],
        reverse=True,
    )



def get_suggested_recipes_by_deals(recipes, limit=5):
    active_deals = list(get_active_deals())
    suggestions = []
    for recipe in recipes.prefetch_related("recipe_ingredients__ingredient"):
        matched_deals = []
        for recipe_ingredient in recipe.recipe_ingredients.all():
            deals = find_deals_for_ingredient(recipe_ingredient.ingredient, active_deals)[:2]
            matched_deals.extend(deals)
        if matched_deals:
            suggestions.append({
                "recipe": recipe,
                "deals": matched_deals[:4],
                "match_count": len(matched_deals),
            })
    suggestions.sort(key=lambda item: item["match_count"], reverse=True)
    return suggestions[:limit]