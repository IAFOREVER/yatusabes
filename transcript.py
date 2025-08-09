import os
import re
from typing import List, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import VideoUnavailable

def _get_proxies() -> Optional[List[str]]:
    """
    Lee y formatea la lista de proxies desde una variable de entorno.
    La variable debe contener los proxies separados por comas.
    Ej: "ip1:port:user:pass,ip2:port:user:pass"
    """
    proxy_env_var = os.getenv("YOUTUBE_PROXIES")
    if not proxy_env_var:
        return None

    # Formatea cada proxy para la librería.
    # El formato esperado es "http://user:pass@ip:port"
    formatted_proxies = []
    for proxy_str in proxy_env_var.split(','):
        try:
            ip, port, user, password = proxy_str.strip().split(':')
            formatted_proxies.append(f"http://{user}:{password}@{ip}:{port}")
        except ValueError:
            # Ignora proxies mal formateados
            print(f"Proxy mal formateado, ignorando: {proxy_str}")
            continue
            
    return formatted_proxies if formatted_proxies else None

def get_transcript_list(video_id: str, languages: Optional[List[str]] = None) -> List[dict]:
    """
    Obtiene la transcripción de un video, utilizando proxies si están disponibles.
    Este método sigue el flujo manual para mayor compatibilidad.
    """
    try:
        proxies = _get_proxies()
        # 1. Listar todas las transcripciones disponibles para el video.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)

        # 2. Encontrar la mejor transcripción según la lista de idiomas preferidos.
        languages_to_try = languages if languages else ['en']
        transcript = transcript_list.find_transcript(languages_to_try)

        # 3. Obtener los datos de la transcripción. El proxy se hereda de la llamada anterior.
        raw_transcript = transcript.fetch()
        
        # 4. Limpiar y formatear el resultado.
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
        # Re-lanza las excepciones esperadas para que main.py las maneje
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
        # CORRECCIÓN: Se utiliza el método correcto para listar transcripciones.
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