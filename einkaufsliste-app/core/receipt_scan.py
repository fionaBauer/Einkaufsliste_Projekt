"""Kassenzettel/Einkaufszettel-Erkennung via OpenAI (Text- oder Vision-Extraktion)."""
import base64
import io
import json
import os

import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image

MAX_PAGES = 3
MAX_IMAGE_EDGE = 1600

SYSTEM_PROMPT = """Du liest deutsche Kassenzettel/Kassenbons oder handschriftliche Einkaufszettel aus \
und extrahierst daraus eine Liste der gekauften bzw. zu kaufenden Lebensmittel/Artikel.

Antworte NUR mit JSON in exakt diesem Schema:
{
  "items": [
    {"raw_name": "Produktname wie er auf dem Zettel steht", "name": "generischer Name", "quantity": "Menge als Zahl-String", "unit": "g|kg|ml|l|pcs|pkg|el|tl"}
  ]
}

Regeln für "name" (generischer Name):
- Gib den generischen Lebensmittelnamen zurück, wie er typischerweise in Rezepten verwendet wird: \
Grundzutat ohne Marke, Verpackungsgröße oder Bio/Sorten-Zusatz. Singular oder wie im allgemeinen \
Sprachgebrauch üblich (z.B. "Kartoffeln", "Bananen", "Eier").
  Beispiele: "KBio. Bananen Kg" -> "Bananen"; "Kartoffeln vfk 2kg" -> "Kartoffeln"; \
"KPur.H.Inn.Brustf." -> "Hähnchenbrustfilet"; "Äpfel Elstar 1kg" -> "Äpfel".
- Bei Markenprodukten ohne generisches Äquivalent (z.B. Getränke-Marken wie "Red Bull Sugarfree") \
bleibt der Markenname als generischer Name stehen — erfinde keine Kategorie dafür.
- WICHTIG: Wenn ein Produkt aus mehreren Bestandteilen besteht oder eine Zubereitung ist (z.B. "Pesto Paprika", \
"Paprika-Aufstrich", "Kartoffelsalat"), ist der generische Name das GESAMTE Produkt (z.B. "Pesto Paprika"), \
NIEMALS nur die Hauptzutat (NICHT "Paprika"). Nur eigenständige Rohware bekommt den reinen Grundnamen.
- "raw_name" bleibt der originale/unveränderte Text vom Zettel (zur Wiedererkennung für den Nutzer).

Weitere Regeln:
- Ignoriere/überspringe: Pfandartikel/Pfand-Zeilen, Rabatte, Gutscheine, Treuepunkte, Summe/Zwischensumme, \
Steuerangaben (z.B. "A 19,00%"), Zahlungsdaten (Karte, Terminal, TA-Nr, EMV, PAN), Filial-/Kassen-/Bon-Nummern, \
Öffnungszeiten, Werbetexte und alles, was kein Lebensmittel/Haushaltsartikel ist.
- Wenn eine Menge in kg/g angegeben ist, übernimm sie so; sonst bei Stückartikeln quantity="1", unit="pcs".
- Wenn auf dem Zettel eine reine Stückzahl vor dem Artikel steht (z.B. "2 * 1,39"), ist das die Stückzahl -> unit="pcs".
- Wenn du dir bei Menge/Einheit nicht sicher bist, nutze quantity="1", unit="pcs".
- Bei einem handschriftlichen Einkaufszettel (Liste geplanter Einkäufe statt Kassenbon) gilt dieselbe Logik; \
raw_name und name können dann identisch sein.
- Wenn du gar keine Artikel erkennen kannst, gib {"items": []} zurück.
"""


def prepare_receipt_input(file_bytes: bytes, content_type: str) -> dict:
    """
    Bereitet die Eingabe für die Extraktion vor.
    Gibt {"text": str} zurück, wenn eine Textebene (PDF) genutzt werden kann,
    sonst {"images": [jpeg_bytes, ...]}.
    """
    if content_type == "application/pdf" or file_bytes[:4] == b"%PDF":
        return _prepare_pdf(file_bytes)
    return {"images": [_normalize_image(file_bytes)]}


def _prepare_pdf(pdf_bytes: bytes) -> dict:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = doc[:MAX_PAGES]
        text = "\n".join(page.get_text().strip() for page in pages).strip()
        if len(text) >= 20:
            return {"text": text}

        images = []
        for page in pages:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            images.append(_normalize_image(pixmap.tobytes("png")))
        return {"images": images}
    finally:
        doc.close()


def _normalize_image(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")

    if max(image.size) > MAX_IMAGE_EDGE:
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def extract_receipt_items(prepared_input: dict) -> list[dict]:
    """Ruft GPT-4o mit Text oder Bildern auf und gibt eine Liste erkannter Artikel zurück."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if "text" in prepared_input:
        user_content = f"=== KASSENZETTEL-TEXT ===\n{prepared_input['text']}"
    else:
        user_content = [{"type": "text", "text": "Lies die Artikel von diesem Kassenzettel/Einkaufszettel aus."}]
        for image_bytes in prepared_input["images"]:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            })

    try:
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
        data = json.loads(raw_text)
        items = data.get("items", [])
        return items if isinstance(items, list) else []
    except Exception:
        return []
