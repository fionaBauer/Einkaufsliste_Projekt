"""Rezeptbilder für das Web verkleinern.

Handyfotos kommen mit 3000–4000 px und mehreren MB an, angezeigt werden sie aber als
Karte (~200 px) oder Titelbild (~800 px). Deshalb wird beim Speichern:
- das Bild auf maximal MAX_SIZE px verkleinert (und nach EXIF richtig gedreht),
- ein Vorschaubild mit THUMB_SIZE px daneben abgelegt (<name>_thumb.jpg).

Die Verarbeitung ist idempotent: Existiert das Vorschaubild schon, passiert nichts.
"""
import logging
import os
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

MAX_SIZE = 1600
THUMB_SIZE = 600
QUALITY = 82


def thumbnail_name(name):
    base, _ = os.path.splitext(name)
    return f"{base}_thumb.jpg"


def _to_rgb(img):
    if img.mode in ("RGB", "L"):
        return img.convert("RGB")
    # Transparenz (PNG) auf weißen Hintergrund legen statt schwarz werden zu lassen
    background = Image.new("RGB", img.size, (255, 255, 255))
    rgba = img.convert("RGBA")
    background.paste(rgba, mask=rgba.split()[-1])
    return background


def _encode_jpeg(img, max_px):
    copy = img.copy()
    copy.thumbnail((max_px, max_px), Image.LANCZOS)
    buffer = BytesIO()
    copy.save(buffer, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buffer.getvalue()


def optimize_recipe_image(field_file):
    """Verkleinert das Bild und legt das Vorschaubild an.

    Gibt den (ggf. neuen) Dateinamen des Hauptbilds zurück, oder None, wenn nichts
    zu tun war bzw. das Bild nicht gelesen werden konnte.
    """
    storage = field_file.storage
    name = field_file.name
    thumb = thumbnail_name(name)

    if storage.exists(thumb):
        return None

    try:
        with storage.open(name, "rb") as f:
            img = Image.open(f)
            img = ImageOps.exif_transpose(img)
            img = _to_rgb(img)
    except Exception:
        logger.exception("Rezeptbild konnte nicht gelesen werden: %s", name)
        return None

    is_jpeg = os.path.splitext(name)[1].lower() in (".jpg", ".jpeg")
    new_name = name

    if max(img.size) > MAX_SIZE or not is_jpeg:
        data = _encode_jpeg(img, MAX_SIZE)
        target = name if is_jpeg else f"{os.path.splitext(name)[0]}.jpg"
        storage.delete(name)
        new_name = storage.save(target, ContentFile(data))

    storage.save(thumbnail_name(new_name), ContentFile(_encode_jpeg(img, THUMB_SIZE)))
    return new_name
