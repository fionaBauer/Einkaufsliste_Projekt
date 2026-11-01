import re
from functools import lru_cache
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


_PAREN = re.compile(r"\(.*?\)")
_TOKEN_SPLIT = re.compile(r"[\s/,&+]+")
_PLURAL_SUFFIXES = ("", "n", "en", "e", "s", "er", "nen")
_UMLAUT = {"a": "ä", "o": "ö", "u": "ü"}

# Zusammensetzungen, die zwar auf den Begriff enden, aber etwas anderes sind
DEAL_EXCLUSIONS = {
    "apfel": ("granatapfel", "zuckerapfel", "erdapfel"),
    "äpfel": ("granatäpfel",),
    "nuss": ("muskatnuss", "kokosnuss"),
    "kohl": ("blumenkohl", "rosenkohl", "grünkohl"),
    "milch": ("buttermilch", "kokosmilch", "hafermilch", "sojamilch", "mandelmilch", "kondensmilch", "sonnenmilch"),
    "sahne": ("sprühsahne",),
    "zucker": ("puderzucker", "vanillezucker"),
}


# Drogerie-/Haushaltsartikel: tauchen bei Marktguru zwischen Lebensmitteln auf
# ("Bodyspray Mango" passt sonst zu "Mango")
NON_FOOD_CATEGORY_WORDS = (
    "deo", "körper", "pflege", "haar", "dusch", "bad ", "kosmetik", "parfum", "duft",
    "zahn", "mund", "rasur", "rasier", "make-up", "nagel", "sonnenschutz", "hygiene",
    "windel", "reinigung", "putz", "wasch", "spülmittel", "tier", "hund", "katze",
    "vogel", "pflanze", "blume", "garten", "haushalt", "papier", "batterie", "kerze",
    "geschirr", "küchengerät", "küchenzubehör", "reisen", "geschenk",
)
NON_FOOD_NAME_WORDS = (
    "spray", "deo", "duschgel", "shampoo", "spülung", "lotion", "parfum", "eau de",
    "zahnpasta", "zahncreme", "waschmittel", "weichspüler", "reiniger", "seife",
    "handcreme", "gesichtscreme", "tagescreme", "nachtcreme", "bodybutter", "lippenpflege",
    "badezusatz", "schaumbad", "duftkerze", "raumduft", "katzenfutter", "hundefutter",
)


def is_non_food(title="", categories=""):
    """True für Drogerie-, Haushalts- und Tierartikel."""
    cats = (categories or "").lower()
    name = (title or "").lower()
    return any(w in cats for w in NON_FOOD_CATEGORY_WORDS) or any(w in name for w in NON_FOOD_NAME_WORDS)


def _umlaut_variant(term):
    """Apfel → äpfel, Wurst → würst(e): deutscher Plural mit Umlaut."""
    for i in range(len(term) - 1, -1, -1):
        if term[i] in _UMLAUT:
            return term[:i] + _UMLAUT[term[i]] + term[i + 1:]
    return None


def search_name(ingredient_name):
    """Normalisierter Name für Suche/Abgleich: klein, ohne Klammerzusätze ("Mais (Dose)" → "mais")."""
    return " ".join(_PAREN.sub(" ", ingredient_name or "").lower().split())


def get_search_terms(ingredient_name):
    """Begriffe, mit denen ein Angebot zu einer Zutat passt.

    Bei mehrteiligen Namen zählt nur das letzte Wort ("Rote Zwiebel" → "zwiebel"),
    sonst passt "Rote" auch zu "Rote Bete".
    """
    name = search_name(ingredient_name)
    if not name:
        return set()
    head = name.split()[-1]
    terms = {head}
    variant = _umlaut_variant(head)
    if variant and len(head) >= 4:
        terms.add(variant)
    for term in list(terms) + [name]:
        terms.update(SYNONYMS.get(term, []))
    return {t for t in terms if len(t) >= 3}


def _product_heads(deal):
    """Wörter des Produktnamens (ohne Marke); bei Bindestrich-Wörtern nur der letzte Teil.

    "Butter-Mandel-Stollen" → ["stollen"], "Bio-Vollmilch" → ["vollmilch"],
    "Meersalz Butter" → ["meersalz", "butter"].
    """
    name = (deal.product_name or deal.title or "").lower()
    heads = []
    for token in _TOKEN_SPLIT.split(name):
        token = token.strip(".-")
        if token:
            heads.append(token.split("-")[-1])
    return heads


@lru_cache(maxsize=1024)
def _map_source_category(name):
    from ingredients.categories import guess_category

    return guess_category(name)


def _deal_categories(deal):
    """Marktguru-Kategorien des Angebots, übersetzt in unsere Kategorien."""
    from ingredients.models import IngredientCategory

    names = [n for n in (getattr(deal, "source_categories", "") or "").split("|") if n]
    return {_map_source_category(n) for n in names} - {IngredientCategory.OTHER}


def _match_info(deal):
    """Pro Angebot nur einmal berechnen (Wortköpfe, Nicht-Lebensmittel, Kategorien).

    Der Abgleich läuft für jede Zutat gegen jedes Angebot – ohne Zwischenspeicher wurde
    jedes Angebot dutzendfach neu zerlegt, was die Seiten bei vielen Angeboten bremste.
    """
    info = getattr(deal, "_match_info", None)
    if info is None:
        info = (
            tuple(_product_heads(deal)),
            is_non_food(f"{deal.title} {deal.product_name or ''}", getattr(deal, "source_categories", "")),
            frozenset(_deal_categories(deal)),
        )
        deal._match_info = info
    return info


def deal_matches(deal, terms, ingredient_category=None):
    """Passt, wenn ein Wort im Produktnamen auf den Begriff endet (inkl. Plural) …

    Deutsche Komposita tragen die Bedeutung am Ende: "Vollmilch" ist Milch,
    "Butterschmalz" aber keine Butter.

    … und die Kategorie nicht widerspricht: Für "Banane" (Obst) zählt "Joghurt Banane"
    (laut Marktguru ein Joghurt) nicht.
    """
    from ingredients.models import IngredientCategory

    heads, non_food, deal_categories = _match_info(deal)

    if ingredient_category != IngredientCategory.OTHER and non_food:
        return False

    name_match = False
    for head in heads:
        for term in terms:
            if head in DEAL_EXCLUSIONS.get(term, ()):
                continue
            if any(head.endswith(term + suffix) for suffix in _PLURAL_SUFFIXES):
                name_match = True
                break
        if name_match:
            break
    if not name_match:
        return False

    if ingredient_category and ingredient_category != IngredientCategory.OTHER:
        if deal_categories and ingredient_category not in deal_categories:
            return False
    return True


def deal_sort_key(deal):
    # Günstigster Grundpreis (€/kg, €/l) zuerst, dann Preis
    return (
        deal.reference_price is None,
        deal.reference_price or 0,
        deal.deal_price is None,
        deal.deal_price or 0,
        deal.store.name,
    )


class DealIndex:
    """Stichwortverzeichnis der Angebote nach Wortenden.

    "Tafeläpfel" landet unter "äpfel", "läpfel", … – eine Zutat schaut so direkt unter
    ihren Begriffen nach, statt jedes Angebot durchzuprobieren. Einmal pro Seitenaufruf bauen.
    """

    def __init__(self, deals):
        self.deals = list(deals)
        self._by_ending = {}
        for deal in self.deals:
            seen = set()
            for head in _match_info(deal)[0]:
                for i in range(len(head) - 2):  # Wortenden ab 3 Buchstaben
                    ending = head[i:]
                    if ending not in seen:
                        seen.add(ending)
                        self._by_ending.setdefault(ending, []).append(deal)

    def candidates(self, terms):
        found = {}
        for term in terms:
            for suffix in _PLURAL_SUFFIXES:
                for deal in self._by_ending.get(term + suffix, ()):
                    found[id(deal)] = deal
        return found.values()


def find_deals_for_ingredient(ingredient, active_deals=None):
    """
    active_deals: optional pre-fetched iterable of Deal objects (list or queryset,
    e.g. from get_active_deals()). Pass this in when matching many ingredients in a
    loop to avoid firing one DB query per ingredient (N+1) - see
    attach_deals_to_shopping_items / get_suggested_recipes_by_deals below.
    """
    deals = active_deals if active_deals is not None else get_active_deals()
    terms = get_search_terms(ingredient.name)
    if not terms:
        return []
    if isinstance(deals, DealIndex):
        deals = deals.candidates(terms)

    category = getattr(ingredient, "category", None)
    matched = [deal for deal in deals if deal_matches(deal, terms, category)]
    matched.sort(key=deal_sort_key)
    return matched


def attach_deals_to_shopping_items(items, active_deals=None):
    deals = active_deals if active_deals is not None else get_active_deals()
    if not isinstance(deals, DealIndex):
        deals = DealIndex(deals)
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
    active_deals = DealIndex(get_active_deals())
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