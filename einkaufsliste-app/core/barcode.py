"""Barcode lookup via Open Food Facts + ingredient matching."""
import requests
from difflib import SequenceMatcher

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"


def lookup_barcode(barcode: str) -> dict:
    """
    Look up a barcode via Open Food Facts.
    Returns dict with 'product_name', 'generic_name', 'found'.
    """
    try:
        url = OPEN_FOOD_FACTS_URL.format(barcode=barcode)
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Prepio/1.0"})
        data = resp.json()

        if data.get("status") != 1:
            return {"found": False, "barcode": barcode}

        product = data.get("product", {})

        # Try to get the best product name
        product_name = (
            product.get("product_name_de")
            or product.get("product_name")
            or product.get("generic_name_de")
            or product.get("generic_name")
            or ""
        ).strip()

        if not product_name:
            return {"found": False, "barcode": barcode}

        return {
            "found": True,
            "barcode": barcode,
            "product_name": product_name,
            "brand": product.get("brands", "").strip(),
            "quantity": product.get("quantity", "").strip(),
        }

    except Exception:
        return {"found": False, "barcode": barcode}


def match_ingredient_name(product_name: str, ingredients) -> str:
    """
    Find the best matching ingredient name from existing ingredients.
    Returns the matched name or the cleaned product name.
    """
    if not product_name:
        return product_name

    # Clean the product name — remove brand/quantity info
    name_lower = product_name.lower()

    best_score = 0
    best_name = None

    for ingredient in ingredients:
        ing_name = ingredient.name.lower()
        # Check if ingredient name is contained in product name or vice versa
        if ing_name in name_lower or name_lower in ing_name:
            score = len(ing_name) / max(len(name_lower), 1)
            if score > best_score:
                best_score = score
                best_name = ingredient.name

        # Fuzzy match
        ratio = SequenceMatcher(None, ing_name, name_lower).ratio()
        if ratio > best_score and ratio > 0.6:
            best_score = ratio
            best_name = ingredient.name

    return best_name or product_name