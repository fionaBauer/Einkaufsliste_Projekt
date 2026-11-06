"""Such- und Filterlogik der Rezeptübersicht."""
from django.db.models import Q

from .models import RecipeIngredient, RecipeTag, Tag, TAG_GROUPS

SORT_OPTIONS = [
    ("name", "Name A–Z"),
    ("-name", "Name Z–A"),
    ("-created_at", "Neueste zuerst"),
    ("created_at", "Älteste zuerst"),
]
DEFAULT_SORT = "name"

# Vegane Rezepte sind auch vegetarisch, müssen aber nicht doppelt zugeordnet werden
TAG_INCLUDES = {Tag.VEGETARIAN.value: [Tag.VEGAN.value]}

_CHICKEN = ["hähnchen", "hühnchen", "huhn", "poulet", "chicken"]
_MINCE = ["hack", "hackfleisch"]
_CARROT = ["karotte", "möhre", "mohrrübe"]
_LEEK = ["lauch", "porree"]
_SHRIMP = ["garnele", "shrimp", "scampi"]
_POTATO = ["kartoffel", "erdapfel"]
_PASTA = [
    "nudel", "pasta", "spaghetti", "penne", "fusilli", "tagliatelle", "makkaroni",
    "farfalle", "rigatoni", "linguine", "tortellini", "ravioli",
]

# Oberbegriff → was alles dazugehört. Nur in diese Richtung: "Nudeln" findet Spaghetti,
# "Spaghetti" aber nicht jedes Nudelgericht.
INGREDIENT_ALIASES = {
    **dict.fromkeys(_CHICKEN, _CHICKEN),
    **dict.fromkeys(_MINCE, _MINCE),
    **dict.fromkeys(_CARROT, _CARROT),
    **dict.fromkeys(_LEEK, _LEEK),
    **dict.fromkeys(_SHRIMP, _SHRIMP),
    **dict.fromkeys(_POTATO, _POTATO),
    "nudel": _PASTA,
    "pasta": _PASTA,
}

_PLURAL_SUFFIXES = ("", "n", "en", "s")


def ingredient_terms(query):
    """Suchbegriffe für eine Zutat inklusive Synonyme ("Hühnchen" → auch "Hähnchen")."""
    normalized = query.lower().strip()
    for base, aliases in INGREDIENT_ALIASES.items():
        if normalized in [base + suffix for suffix in _PLURAL_SUFFIXES]:
            return [normalized, *aliases]
    return [normalized]


def _recipes_with_ingredient(query):
    matches = Q()
    for term in ingredient_terms(query):
        matches |= Q(ingredient__name__icontains=term)
    return RecipeIngredient.objects.filter(matches).values("recipe")


def _recipes_with_any_tag(tags):
    return RecipeTag.objects.filter(tag__in=tags).values("recipe")


class RecipeFilters:
    """Liest die Filter aus der URL und wendet sie auf die Rezepte an."""

    def __init__(self, params):
        self.params = params
        self.search = params.get("search", "").strip()
        self.tags = [tag for tag in Tag.values if tag in params.getlist("tag")]
        self.ingredients = list(dict.fromkeys(
            name.strip() for name in params.getlist("ingredient") if name.strip()
        ))
        self.deals_only = bool(params.get("deals"))
        sort = params.get("sort", DEFAULT_SORT)
        self.sort = sort if sort in dict(SORT_OPTIONS) else DEFAULT_SORT

    def apply(self, recipes, recipe_ids_with_deals):
        if self.search:
            recipes = recipes.filter(
                Q(name__icontains=self.search) | Q(pk__in=_recipes_with_ingredient(self.search))
            )

        for group in TAG_GROUPS:
            selected = [tag.value for tag in group["tags"] if tag.value in self.tags]
            if not selected:
                continue
            if group.get("match_all"):
                for tag in selected:
                    recipes = recipes.filter(pk__in=_recipes_with_any_tag([tag]))
            else:
                included = [
                    tag for selected_tag in selected
                    for tag in [selected_tag, *TAG_INCLUDES.get(selected_tag, [])]
                ]
                recipes = recipes.filter(pk__in=_recipes_with_any_tag(included))

        for ingredient in self.ingredients:
            recipes = recipes.filter(pk__in=_recipes_with_ingredient(ingredient))

        if self.deals_only:
            recipes = recipes.filter(pk__in=recipe_ids_with_deals)

        return recipes.order_by(self.sort)

    def groups(self):
        return [
            {
                "label": group["label"],
                "options": [
                    {"value": tag.value, "label": tag.label, "selected": tag.value in self.tags}
                    for tag in group["tags"]
                ],
            }
            for group in TAG_GROUPS
        ]

    def sort_options(self):
        return SORT_OPTIONS

    def chips(self):
        """Aktive Filter als Chips, jeder mit der URL-Query ohne diesen Filter."""
        chips = [{"label": Tag(tag).label, "query": self._query_without("tag", tag)} for tag in self.tags]
        chips += [
            {"label": name, "query": self._query_without("ingredient", name)}
            for name in self.ingredients
        ]
        if self.deals_only:
            chips.append({"label": "Mit Rabatt", "query": self._query_without("deals")})
        return chips

    def _query_without(self, key, value=None):
        params = self.params.copy()
        if value is None:
            params.pop(key, None)
        else:
            params.setlist(key, [item for item in params.getlist(key) if item != value])
        return params.urlencode()

    @property
    def active_count(self):
        return len(self.chips())

    @property
    def is_filtered(self):
        return bool(self.search or self.active_count)

    @property
    def is_modified(self):
        return self.is_filtered or self.sort != DEFAULT_SORT
