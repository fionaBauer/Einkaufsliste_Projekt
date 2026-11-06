import json
import os

from openai import OpenAI

from recipes.models import Tag

CATEGORY_RULES = """- tags: Ordne das Rezept passenden Kategorien aus der Liste unten zu und gib nur deren Kürzel an. Die Kategorien darfst du aus Zutaten und Zubereitung ableiten. Vergib möglichst je eine Kategorie für Mahlzeit, Art und Inhalt; lass nur weg, was du nicht sicher beurteilen kannst. "vegan" nur, wenn gar keine tierischen Produkte vorkommen. "quick" nur bei höchstens 30 Minuten
- cooking_minutes: Ungefähre Gesamtzeit für Vorbereitung und Kochen in Minuten als ganze Zahl. Wenn keine Zeit genannt wird, schätze sie anhand von Zutaten und Schritten

Erlaubte Tags:
""" + "\n".join(f"- {tag.value}: {tag.label}" for tag in Tag)

SYSTEM_PROMPT = """Du bist ein Rezept-Extraktions-Experte. Du bekommst den Transcript-Text und/oder die Caption eines Koch-Videos.

Extrahiere daraus ein strukturiertes Rezept als JSON mit exakt diesem Schema:
{
  "title": "Name des Rezepts",
  "description": "Kurze Beschreibung",
  "servings": "Portionen (z.B. '4 Portionen')",
  "prep_time": "Vorbereitungszeit",
  "cook_time": "Kochzeit",
  "cooking_minutes": 30,
  "ingredients": [
    {"name": "Zutat", "amount": "Menge als String", "unit": "Einheit"}
  ],
  "steps": [
    {"order": 1, "instruction": "Schritt-Anleitung", "duration": "Dauer falls genannt"}
  ],
  "tags": ["tag1", "tag2"]
}

Regeln:
- Antworte IMMER auf Deutsch, unabhängig von der Sprache des Transcripts
- Extrahiere NUR was im Video/Caption tatsächlich genannt wird (Ausnahme: tags und cooking_minutes)
- Wenn Mengen nicht genannt werden, setze amount und unit auf null
- Schreibe die Schritte in der Reihenfolge wie im Video gezeigt
- Antworte NUR mit dem JSON, kein anderer Text
""" + CATEGORY_RULES

CLASSIFY_PROMPT = """Du ordnest ein fertig strukturiertes Rezept in Kategorien ein.

Antworte NUR mit JSON in exakt diesem Schema:
{"tags": ["tag1", "tag2"], "cooking_minutes": 30}

Regeln:
""" + CATEGORY_RULES


def extract_recipe(transcript: str | None, caption: str | None, source_url: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_content = _build_user_message(transcript, caption)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content.strip()
    recipe_data = json.loads(raw_text)
    recipe_data["source_url"] = source_url
    return recipe_data


def classify_recipe(recipe: dict) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ingredients = ", ".join(item.get("name") or "" for item in recipe.get("ingredients") or [])
    steps = "\n".join(step.get("instruction") or "" for step in recipe.get("steps") or [])
    user_content = (
        f"=== TITEL ===\n{recipe.get('title') or ''}\n\n"
        f"=== STICHWÖRTER DER SEITE ===\n{', '.join(recipe.get('tags') or [])}\n\n"
        f"=== ZUTATEN ===\n{ingredients}\n\n"
        f"=== ZUBEREITUNG ===\n{steps}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=300,
        messages=[
            {"role": "system", "content": CLASSIFY_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content.strip())


def _build_user_message(transcript: str | None, caption: str | None) -> str:
    parts = []

    if caption:
        parts.append(f"=== CAPTION ===\n{caption}")

    if transcript:
        parts.append(f"=== TRANSCRIPT ===\n{transcript}")

    if not parts:
        raise ValueError("Weder Transcript noch Caption verfügbar")

    return "\n\n".join(parts)

def extract_recipe_from_webpage_text(page_title: str | None, page_text: str, source_url: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    user_content = (
        f"=== SEITENTITEL ===\n{page_title or ''}\n\n"
        f"=== WEBSEITENTEXT ===\n{page_text}\n\n"
        "Extrahiere daraus ein Rezept. Falls auf der Seite mehrere Inhalte sind, "
        "nimm das wahrscheinlichste Hauptrezept."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content.strip()
    recipe_data = json.loads(raw_text)
    recipe_data["source_url"] = source_url
    return recipe_data