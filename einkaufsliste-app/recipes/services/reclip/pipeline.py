from urllib.parse import urlparse

from .llm_extractor import extract_recipe, extract_recipe_from_webpage_text
from .transcriber import transcribe_video
from .video_extractor import extract_metadata, extract_subtitles
from .web_extractor import extract_recipe_from_webpage, extract_webpage_text


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
    metadata = extract_metadata(url)
    caption = metadata.get("description", "")

    transcript = extract_subtitles(url)

    if not transcript:
        transcript = transcribe_video(url)

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


def _process_web_url(url: str) -> dict:
    recipe = extract_recipe_from_webpage(url)

    has_good_structure = bool(recipe.get("ingredients")) and bool(recipe.get("steps"))

    if has_good_structure:
        return {
            "recipe": recipe,
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