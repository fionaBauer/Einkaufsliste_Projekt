import json
import os

from openai import OpenAI

SYSTEM_PROMPT = """Du bist ein Rezept-Extraktions-Experte. Du bekommst den Transcript-Text und/oder die Caption eines Koch-Videos.

Extrahiere daraus ein strukturiertes Rezept als JSON mit exakt diesem Schema:
{
  "title": "Name des Rezepts",
  "description": "Kurze Beschreibung",
  "servings": "Portionen (z.B. '4 Portionen')",
  "prep_time": "Vorbereitungszeit",
  "cook_time": "Kochzeit",
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
- Extrahiere NUR was im Video/Caption tatsächlich genannt wird
- Wenn Mengen nicht genannt werden, setze amount und unit auf null
- Schreibe die Schritte in der Reihenfolge wie im Video gezeigt
- Tags: Küche-Stil, Diät-Info, Schwierigkeit etc.
- Antworte NUR mit dem JSON, kein anderer Text
"""


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