"""Kategorie-Icons (Namen der Linien-Icons) und automatische Kategorie-Erkennung anhand des Zutatennamens."""
import re

from .models import IngredientCategory

# Name des Linien-Icons in templates/includes/icon.html (gleich dem Kategorie-Wert)
CATEGORY_ICONS = {category: category.value for category in IngredientCategory}
CATEGORY_ICONS[IngredientCategory.OTHER] = "box"

# Reihenfolge ist wichtig: spezifische Begriffe zuerst (z.B. "Paprikapulver" ist ein Gewürz,
# kein Gemüse; "Kokosmilch" eine Konserve, kein Milchprodukt; "Erdnussbutter" ein Aufstrich).
# Kurze Begriffe (<= 3 Zeichen) müssen ein ganzes Wort sein, längere dürfen Teil eines Wortes sein.
CATEGORY_KEYWORDS = [
    # Ausnahmen zuerst: Wörter, die einen irreführenden Teilbegriff enthalten
    # ("Limette" enthält "mett", "Rucola" enthält "cola", "Weintrauben" enthält "wein" …)
    (IngredientCategory.FRUIT_VEG, ["limette", "weintraube", "honigmelone", "rucola"]),
    (IngredientCategory.CANNED, ["gewürzgurke"]),
    (IngredientCategory.SNACKS, ["salzstange", "schokodrops"]),
    # Nicht-Lebensmittel ("Zahnpasta" ist keine Pasta)
    (IngredientCategory.OTHER, ["proteinpulver", "protein", "zahnpasta", "zahnbürste", "spülmittel",
                                "waschmittel", "toilettenpapier", "klopapier", "küchenrolle",
                                "taschentücher", "shampoo", "duschgel", "seife", "müllbeutel",
                                "alufolie", "frischhaltefolie", "backpapier", "schwamm"]),
    (IngredientCategory.FRUIT_VEG, ["wassermelone"]),
    (IngredientCategory.SPICES, ["paprikapulver", "knoblauchpulver", "chilipulver", "currypulver",
                                 "gewürz", "salz", "pfeffer", "curry", "zimt", "oregano", "kümmel",
                                 "muskat", "kurkuma", "garam masala", "chiliflocken", "thymian",
                                 "rosmarin", "basilikum", "essig", "sauce", "soße", "ketchup", "senf",
                                 "mayo", "brühe", "bouillon", "pesto", "paste", "dressing"]),
    (IngredientCategory.CANNED, ["kokosmilch", "dose", "konserve", "kidneybohnen", "kichererbsen",
                                 "linsen", "passierte", "gehackte tomaten", "tomatenmark", "mais"]),
    (IngredientCategory.SNACKS, ["erdnussbutter", "nutella", "schoko", "chips", "keks", "gummibär",
                                 "riegel", "nüsse", "nuss", "mandel", "popcorn", "cracker", "praline"]),
    (IngredientCategory.FREEZER, ["tiefkühl", "tk", "pommes", "gemüsepfanne", "eis", "fischstäbchen"]),
    (IngredientCategory.MEAT_FISH, ["hähnchen", "hühnchen", "huhn", "chicken", "pute", "rind", "schwein",
                                    "hack", "steak", "schnitzel", "wurst", "würstchen", "salami",
                                    "schinken", "speck", "bacon", "lachs", "thunfisch", "fisch",
                                    "garnele", "shrimp", "kabeljau", "forelle", "nuggets", "lamm",
                                    "ente", "chorizo", "mett", "gyros", "döner"]),
    (IngredientCategory.DAIRY, ["milch", "joghurt", "jogurt", "skyr", "quark", "käse", "mozzarella",
                                "parmesan", "feta", "halloumi", "gouda", "emmentaler", "cheddar",
                                "edamer", "camembert", "brie", "mascarpone", "burrata", "gorgonzola", "butter", "sahne", "schmand",
                                "crème", "creme", "frischkäse", "ricotta", "eier", "ei"]),
    (IngredientCategory.BREAD, ["brot", "brötchen", "toast", "baguette", "croissant", "wrap", "tortilla",
                                "brezel", "laugen", "bagel", "ciabatta", "fladen", "kuchen",
                                "backwaren", "gebäck"]),
    (IngredientCategory.GRAINS, ["nudel", "pasta", "spaghetti", "penne", "fusilli", "lasagne", "tagliatelle",
                                 "reis", "couscous", "bulgur", "quinoa", "hafer", "müsli", "muesli",
                                 "cornflakes", "gnocchi", "polenta", "getreide"]),
    (IngredientCategory.BAKING, ["mehl", "zucker", "backpulver", "hefe", "vanille", "kakao", "stärke",
                                 "honig", "sirup", "natron", "gelatine"]),
    (IngredientCategory.DRINKS, ["wasser", "saft", "cola", "limo", "sprudel", "bier", "wein", "kaffee",
                                 "tee", "redbull", "red bull", "energy", "smoothie", "schorle", "eistee",
                                 "softdrink", "getränk", "spirituose"]),
    (IngredientCategory.FRUIT_VEG, ["apfel", "äpfel", "banane", "birne", "orange", "zitrone", "limette",
                                    "beere", "traube", "mango", "ananas", "kiwi", "tomate", "gurke",
                                    "paprika", "zwiebel", "knoblauch", "karotte", "möhre", "kartoffel",
                                    "salat", "spinat", "brokkoli", "zucchini", "aubergine", "pilz",
                                    "champignon", "avocado", "lauch", "kohl", "sellerie", "ingwer",
                                    "kürbis", "radieschen", "rucola", "petersilie", "schnittlauch",
                                    "bohnen", "erbsen", "gemüse", "obst", "melone", "pfirsich",
                                    "frucht", "früchte", "zitrusfrüchte", "kräuter"]),
]


def _matches(name, words, keyword):
    if len(keyword) <= 3:
        return keyword in words
    return keyword in name


_seed_lookup = None


def _seed_category(normalized):
    """Exakter Treffer im eingebauten Wörterbuch (seed_data.py)."""
    global _seed_lookup
    if _seed_lookup is None:
        from .seed_data import iter_seed_ingredients

        _seed_lookup = {name.lower(): category for name, category, _ in iter_seed_ingredients()}
    return _seed_lookup.get(normalized)


def guess_category(name, default=IngredientCategory.OTHER):
    """Ordnet einen Zutatennamen einer Kategorie zu (oder default, wenn nichts passt).

    Zuerst das Wörterbuch (exakter Name), dann Stichwörter im Namen.
    """
    normalized = (name or "").lower().strip()
    seeded = _seed_category(normalized)
    if seeded:
        return seeded
    words = set(re.split(r"[^a-zäöüß]+", normalized))
    # Öle ("Olivenöl", "Rapsöl") enden auf "öl" – als Teilwort zu kurz für die Regel oben
    if any(w.endswith("öl") for w in words if w):
        return IngredientCategory.SPICES
    # Teesorten ("Pfefferminztee") – "eistee" steht explizit bei den Getränken
    if any(w.endswith("tee") and w != "tee" for w in words if w):
        return IngredientCategory.DRINKS
    for category, keywords in CATEGORY_KEYWORDS:
        if any(_matches(normalized, words, kw) for kw in keywords):
            return category
    return default
