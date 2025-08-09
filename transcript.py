import os
import re
from typing import List, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import VideoUnavailable

def _get_proxies() -> Optional[List[str]]:
    """
    Lee y formatea la lista de proxies desde una variable de entorno.
    """
    proxy_env_var = os.getenv("YOUTUBE_PROXIES")
    if not proxy_env_var:
        return None

    formatted_proxies = []
    for proxy_str in proxy_env_var.split(','):
        try:
            ip, port, user, password = proxy_str.strip().split(':')
            formatted_proxies.append(f"http://{user}:{password}@{ip}:{port}")
        except ValueError:
            print(f"Proxy mal formateado, ignorando: {proxy_str}")
            continue
            
    return formatted_proxies if formatted_proxies else None

def get_transcript_list(video_id: str, languages: Optional[List[str]] = None) -> List[dict]:
    """
    Obtiene la transcripción de un video, utilizando proxies si están disponibles.
    Usa los métodos estáticos de la librería, compatibles con versiones nuevas.
    """
    try:
        proxies = _get_proxies()
        languages_to_try = languages if languages else ['en']
        
        # Este método estático busca y obtiene la transcripción en un solo paso.
        raw_transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages_to_try, proxies=proxies
        )
        
        # Limpiar y formatear el resultado.
        def clean_text(text: str) -> str:
            cleaned = re.sub(r"[♪♫♬]", "", text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned

        result = []
        for seg in raw_transcript:
            cleaned_text = clean_text(seg.get("text", ""))
            result.append({
                "text": cleaned_text,
                "start": seg.get("start", 0),
                "duration": seg.get("duration", 0),
            })
        return result
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        raise
    except Exception as e:
        print(f"Error inesperado en get_transcript_list: {e}")
        raise RuntimeError(f"Error al obtener la transcripción: {e}")

def get_available_languages(video_id: str) -> List[str]:
    """
    Obtiene los idiomas disponibles, utilizando proxies si están disponibles.
    """
    try:
        proxies = _get_proxies()
        # --- CORRECCIÓN FINAL ---
        # Se usa el método estático .list_transcripts() que es compatible
        # con la nueva versión de la librería y acepta proxies.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
        return [t.language_code for t in transcript_list]
    except (TranscriptsDisabled, VideoUnavailable) as e:
        raise
    except Exception as e:
        print(f"Error inesperado en get_available_languages: {e}")
        raise RuntimeError(f"Error al obtener idiomas disponibles: {e}")

def to_srt(transcript: List[dict]) -> str:
    """
    Convierte la transcripción a formato SRT. (Sin cambios)
    """
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