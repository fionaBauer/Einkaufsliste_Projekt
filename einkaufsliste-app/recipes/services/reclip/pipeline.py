import logging
from urllib.parse import urlparse

from yt_dlp.utils import DownloadError

from .llm_extractor import classify_recipe, extract_recipe, extract_recipe_from_webpage_text
from .transcriber import transcribe_video
from .video_extractor import extract_metadata, extract_subtitles
from .web_extractor import extract_recipe_from_webpage, extract_webpage_text


logger = logging.getLogger(__name__)

VIDEO_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "tiktok.com",
    "www.tiktok.com",
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "fb.watch",
}


def process_url(url: str) -> dict:
    if _is_video_url(url):
        return _process_video_url(url)

    return _process_web_url(url)


def _is_video_url(url: str) -> bool:
    netloc = urlparse(url).netloc.lower()
    return netloc in VIDEO_DOMAINS


def _process_video_url(url: str) -> dict:
    try:
        metadata = extract_metadata(url)
        caption = metadata.get("description", "")

        transcript = extract_subtitles(url)

        if not transcript:
            transcript = transcribe_video(url)
    except DownloadError as error:
        logger.warning("Video konnte nicht geladen werden: %s", error)
        raise ValueError(
            "Das Video konnte nicht geladen werden. Der Beitrag ist vielleicht privat oder die "
            "Plattform blockiert gerade den Zugriff. Du kannst die Beschreibung kopieren und "
            "unter „Text einfügen“ importieren."
        ) from error

    recipe = extract_recipe(
        transcript=transcript,
        caption=caption or None,
        source_url=url,
    )

    return {
        "recipe": recipe,
        "raw_transcript": transcript,
        "raw_caption": caption or None,
    }


def _add_categories(recipe: dict) -> dict:
    """Strukturierte Rezeptseiten kommen ohne KI aus, Kategorien liefern sie aber nicht.

    Scheitert dieser Schritt, geht das Rezept trotzdem durch: Im Prüf-Dialog lassen sich
    die Kategorien auch von Hand setzen.
    """
    try:
        classification = classify_recipe(recipe)
    except Exception:
        logger.exception("Rezept konnte nicht kategorisiert werden")
        return recipe

    recipe["tags"] = classification.get("tags") or []
    recipe["cooking_minutes"] = recipe.get("cooking_minutes") or classification.get("cooking_minutes")
    return recipe


def _process_web_url(url: str) -> dict:
    recipe = extract_recipe_from_webpage(url)

    has_good_structure = bool(recipe.get("ingredients")) and bool(recipe.get("steps"))

    if has_good_structure:
        return {
            "recipe": _add_categories(recipe),
            "raw_transcript": None,
            "raw_caption": None,
        }

    page_data = extract_webpage_text(url)

    llm_recipe = extract_recipe_from_webpage_text(
        page_title=page_data.get("title"),
        page_text=page_data.get("text", ""),
        source_url=url,
    )

    return {
        "recipe": llm_recipe,
        "raw_transcript": None,
        "raw_caption": None,
    }