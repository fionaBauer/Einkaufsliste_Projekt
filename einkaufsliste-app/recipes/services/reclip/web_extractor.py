import json
import re

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def extract_recipe_from_webpage(url: str) -> dict:
    html = _download_html(url)
    soup = BeautifulSoup(html, "html.parser")

    recipe = _extract_from_json_ld(soup)
    if recipe:
        recipe["source_url"] = url
        return recipe

    fallback_recipe = _extract_from_visible_html(soup, url)
    fallback_recipe["source_url"] = url
    return fallback_recipe


def extract_webpage_text(url: str) -> dict:
    html = _download_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True) or title

    for tag in soup(["script", "style", "noscript", "svg", "img", "header", "footer"]):
        tag.decompose()

    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("body")
        or soup
    )

    text = main_content.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = text[:20000]

    return {
        "title": title,
        "text": text,
        "url": url,
    }


def _download_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def _extract_from_json_ld(soup: BeautifulSoup) -> dict | None:
    script_tags = soup.find_all("script", type="application/ld+json")

    for script in script_tags:
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        recipe_obj = _find_recipe_object(data)
        if recipe_obj:
            return _normalize_recipe_json_ld(recipe_obj)

    return None


def _find_recipe_object(data):
    if isinstance(data, dict):
        if data.get("@type") == "Recipe":
            return data

        if isinstance(data.get("@type"), list) and "Recipe" in data.get("@type", []):
            return data

        if "@graph" in data:
            for item in data["@graph"]:
                found = _find_recipe_object(item)
                if found:
                    return found

        for value in data.values():
            found = _find_recipe_object(value)
            if found:
                return found

    if isinstance(data, list):
        for item in data:
            found = _find_recipe_object(item)
            if found:
                return found

    return None


def _normalize_recipe_json_ld(recipe_obj: dict) -> dict:
    ingredients = []
    for item in recipe_obj.get("recipeIngredient", []):
        parsed = _split_ingredient_line(item)
        ingredients.append({
            "name": parsed["name"],
            "amount": parsed["amount"],
            "unit": parsed["unit"],
            "notes": parsed["notes"],
        })

    steps = []
    raw_instructions = recipe_obj.get("recipeInstructions", [])

    if isinstance(raw_instructions, str):
        raw_instructions = [raw_instructions]

    if isinstance(raw_instructions, list):
        order = 1
        for entry in raw_instructions:
            if isinstance(entry, str):
                text = entry.strip()
                if text:
                    steps.append({
                        "order": order,
                        "instruction": text,
                        "duration": "",
                    })
                    order += 1
            elif isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("name")
                    or ""
                ).strip()
                if text:
                    steps.append({
                        "order": order,
                        "instruction": text,
                        "duration": "",
                    })
                    order += 1

    servings = recipe_obj.get("recipeYield", "")
    if isinstance(servings, list):
        servings = servings[0] if servings else ""

    tags = []
    for key in ["recipeCategory", "recipeCuisine", "keywords"]:
        value = recipe_obj.get(key)
        if isinstance(value, str):
            tags.extend([part.strip() for part in value.split(",") if part.strip()])
        elif isinstance(value, list):
            tags.extend([str(part).strip() for part in value if str(part).strip()])

    return {
        "title": (recipe_obj.get("name") or "").strip(),
        "description": (recipe_obj.get("description") or "").strip(),
        "servings": str(servings).strip(),
        "prep_time": str(recipe_obj.get("prepTime") or "").strip(),
        "cook_time": str(recipe_obj.get("cookTime") or "").strip(),
        "ingredients": ingredients,
        "steps": steps,
        "tags": list(dict.fromkeys(tags)),
    }


def _extract_from_visible_html(soup: BeautifulSoup, url: str) -> dict:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else "Extrahiertes Rezept"

    ingredient_lines = _find_candidate_lines(
        soup,
        ["ingredient", "zutat", "zutaten"]
    )
    instruction_lines = _find_candidate_lines(
        soup,
        ["instruction", "anleitung", "zubereitung", "directions", "method"]
    )

    ingredients = []
    for line in ingredient_lines:
        parsed = _split_ingredient_line(line)
        if parsed["name"]:
            ingredients.append(parsed)

    steps = []
    for index, line in enumerate(instruction_lines, start=1):
        steps.append({
            "order": index,
            "instruction": line,
            "duration": "",
        })

    return {
        "title": title,
        "description": "",
        "servings": "",
        "prep_time": "",
        "cook_time": "",
        "ingredients": ingredients,
        "steps": steps,
        "tags": [],
        "source_url": url,
    }


def _find_candidate_lines(soup: BeautifulSoup, keywords: list[str]) -> list[str]:
    results = []

    candidate_nodes = soup.find_all(
        lambda tag: tag.name in ["section", "div", "ul", "ol", "article"]
        and any(
            keyword in " ".join(
                filter(
                    None,
                    [
                        tag.get("id", ""),
                        " ".join(tag.get("class", [])),
                        tag.get_text(" ", strip=True)[:200].lower(),
                    ],
                )
            ).lower()
            for keyword in keywords
        )
    )

    for node in candidate_nodes:
        items = node.find_all(["li", "p"])
        for item in items:
            text = item.get_text(" ", strip=True)
            if text and text not in results:
                results.append(text)

    return results[:50]


def _split_ingredient_line(line: str) -> dict:
    text = re.sub(r"\s+", " ", (line or "").strip())

    pattern = (
        r"^(?P<amount>\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?)?"
        r"\s*"
        r"(?P<unit>kg|g|ml|l|el|tl|pcs|stück|stueck|esslöffel|essloeffel|teelöffel|teeloeffel)?"
        r"\s*"
        r"(?P<name>.+)$"
    )

    match = re.match(pattern, text, flags=re.IGNORECASE)
    if not match:
        return {
            "name": text,
            "amount": "",
            "unit": "",
            "notes": "",
        }

    amount = (match.group("amount") or "").strip()
    unit = (match.group("unit") or "").strip()
    name = (match.group("name") or "").strip(" ,;-")

    return {
        "name": name,
        "amount": amount,
        "unit": unit,
        "notes": "",
    }