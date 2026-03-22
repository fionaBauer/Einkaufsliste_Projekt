import json
import tempfile
from pathlib import Path

import yt_dlp


def extract_metadata(url: str) -> dict:
    with yt_dlp.YoutubeDL({
        "quiet": True,
        "skip_download": True,
        "writeinfojson": False,
    }) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "uploader": info.get("uploader", ""),
        "subtitles": info.get("subtitles", {}),
        "automatic_captions": info.get("automatic_captions", {}),
    }


def extract_subtitles(url: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            "quiet": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "de", "en.*"],
            "subtitlesformat": "json3/srv3/vtt/best",
            "outtmpl": str(Path(tmpdir) / "%(id)s"),
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        for sub_file in Path(tmpdir).glob("*.vtt"):
            return _parse_vtt(sub_file.read_text(encoding="utf-8", errors="ignore"))

        for sub_file in Path(tmpdir).glob("*.json3"):
            return _parse_json3(sub_file.read_text(encoding="utf-8", errors="ignore"))

    return None


def download_audio(url: str, output_dir: str) -> Path:
    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": str(Path(output_dir) / "%(id)s.%(ext)s"),
        "ffmpeg_location": "/opt/homebrew/bin",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }
        ],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]

    for file_path in Path(output_dir).glob(f"{video_id}.*"):
        if file_path.suffix in (".mp3", ".m4a", ".wav", ".opus"):
            return file_path

    raise FileNotFoundError(f"Audio file not found for {video_id}")


def _parse_vtt(content: str) -> str:
    lines = []

    for line in content.split("\n"):
        line = line.strip()

        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
            continue

        if line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
            continue

        if line not in lines:
            lines.append(line)

    return " ".join(lines)


def _parse_json3(content: str) -> str:
    data = json.loads(content)
    segments = data.get("events", [])
    texts = []

    for seg in segments:
        for subsegment in seg.get("segs", []):
            text = subsegment.get("utf8", "").strip()
            if text and text != "\n":
                texts.append(text)

    return " ".join(texts)