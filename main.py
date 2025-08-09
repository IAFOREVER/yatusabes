import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from transcript import get_transcript_list, to_srt, get_available_languages
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound

# Se crea la instancia de la aplicación FastAPI
app = FastAPI()

# --- Habilitar CORS ---
origins = [
    "https://ia-tusabes.web.app",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Conexión a Redis ---
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("La variable de entorno REDIS_URL no está definida")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", 3600))


@app.get("/")
def read_root():
    """
    Endpoint raíz para verificar que la API está funcionando.
    Se añade un número de versión para confirmar que el despliegue fue exitoso.
    """
    return {
        "status": "ok",
        "message": "API de transcripciones funcionando",
        "version": "2.0"  # Indicador de la nueva versión
    }


@app.get("/transcript")
async def transcript(
    video_id: str,
    languages: str = Query("en", description="Lista de códigos de idioma separados por comas"),
    format: str = Query("json", regex="^(json|srt)$", description="Formato de respuesta: json o srt"),
):
    langs = [lang.strip() for lang in languages.split(",") if lang.strip()]
    cache_key = f"transcript:{video_id}:{','.join(langs)}:{format}"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            media_type = "application/json" if format == "json" else "text/plain"
            return PlainTextResponse(content=cached, media_type=media_type)
    except Exception as e:
        print(f"ERROR al acceder a Redis: {e}")

    try:
        transcript_data = get_transcript_list(video_id, langs)
    except TranscriptsDisabled as e:
        print(f"ERROR: TranscriptsDisabled para video_id: {video_id}. Excepción: {e}")
        raise HTTPException(status_code=404, detail="Las transcripciones están deshabilitadas para este video.")
    except NoTranscriptFound as e:
        print(f"ERROR: NoTranscriptFound para video_id: {video_id}. Excepción: {e}")
        raise HTTPException(status_code=404, detail="No se encontró una transcripción para el video y los idiomas dados.")
    except Exception as e:
        print(f"ERROR: Excepción genérica en /transcript para video_id: {video_id}. Excepción: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if format == "json":
        response_content = json.dumps(transcript_data, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        response_content = to_srt(transcript_data)
        media_type = "text/plain"

    try:
        await redis_client.setex(cache_key, REDIS_CACHE_TTL, response_content)
    except Exception as e:
        print(f"ERROR al guardar en Redis: {e}")

    return PlainTextResponse(content=response_content, media_type=media_type)


@app.get("/transcript/languages")
async def available_languages(video_id: str):
    try:
        langs = get_available_languages(video_id)
        return JSONResponse(content={"video_id": video_id, "available_languages": langs})
    except TranscriptsDisabled as e:
        print(f"ERROR: TranscriptsDisabled en /languages para video_id: {video_id}. Excepción: {e}")
        raise HTTPException(status_code=404, detail="Las transcripciones están deshabilitadas para este video.")
    except Exception as e:
        print(f"ERROR: Excepción genérica en /languages para video_id: {video_id}. Excepción: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()