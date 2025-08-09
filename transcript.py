from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import VideoUnavailable
from typing import List, Optional
import re

def get_transcript_list(video_id: str, languages: Optional[List[str]] = None) -> List[dict]:
    try:
        languages_to_try = languages if languages else ["en"]
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Buscar el subtítulo más adecuado
        transcript = transcript_list.find_transcript(languages_to_try)
        raw_transcript = transcript.fetch()

        def clean_text(text: str) -> str:
            cleaned = re.sub(r"[♪♫♬]", "", text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned

        result = []
        for seg in raw_transcript:
            if isinstance(seg, dict):
                text = seg.get("text", "")
                start = seg.get("start", 0)
                duration = seg.get("duration", 0)
            else:
                text = getattr(seg, "text", "")
                start = getattr(seg, "start", 0)
                duration = getattr(seg, "duration", 0)

            cleaned_text = clean_text(text)
            result.append({
                "text": cleaned_text,
                "start": start,
                "duration": duration,
            })
        return result
    except TranscriptsDisabled:
        raise
    except NoTranscriptFound:
        raise
    except Exception as e:
        raise RuntimeError(f"Error al obtener la transcripción: {e}")

def get_available_languages(video_id: str) -> List[str]:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcripts = ytt_api.list(video_id)
        return [t.language_code for t in transcripts]
    except TranscriptsDisabled:
        raise
    except VideoUnavailable:
        raise
    except Exception as e:
        raise RuntimeError(f"Error al obtener idiomas disponibles: {e}")

def to_srt(transcript: List[dict]) -> str:
    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(transcript, 1):
        start = seg.get("start", 0)
        dur = seg.get("duration", 0)
        end = start + dur
        text = seg.get("text", "")
        lines.append(f"{i}\n{format_time(start)} --> {format_time(end)}\n{text}\n")
    return "\n".join(lines)