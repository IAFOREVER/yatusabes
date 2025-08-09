import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from transcript import get_transcript_list, to_srt, get_available_languages
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound

# --- Tarea 2: Habilitar CORS ---
# Se crea la instancia de la aplicación FastAPI
app = FastAPI()

# Se define la lista de orígenes permitidos para CORS.
# Esto es crucial para que tu frontend en Firebase pueda comunicarse con esta API.
origins = [
    "https://ia-tusabes.web.app",  # URL de producción en Firebase
    "http://localhost:5000",      # URL para pruebas locales del frontend
    "http://127.0.0.1:5000",     # Otra URL común para pruebas locales
]

# Se añade el middleware de CORS a la aplicación FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
)
# --- Fin de la Tarea 2 ---


# --- Tarea 1: Modificar la conexión a Redis ---
# Se obtiene la URL de conexión a Redis desde las variables de entorno.
# Render.com proporcionará esta URL automáticamente.
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    # Si la variable no está definida, se lanza un error para detener la ejecución.
    raise ValueError("La variable de entorno REDIS_URL no está definida")

# Se crea el cliente de Redis usando la URL, lo que simplifica la configuración.
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
# --- Fin de la Tarea 1 ---


# Se obtiene el tiempo de vida (TTL) para el caché de Redis desde las variables de entorno.
# Se usa un valor por defecto de 3600 segundos (1 hora) si no está definido.
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", 3600))


@app.get("/")
def read_root():
    """
    Endpoint raíz para verificar que la API está funcionando.
    Render.com usa esto como un 'health check'.
    """
    return {"status": "ok", "message": "API de transcripciones funcionando"}


@app.get("/transcript")
async def transcript(
    video_id: str,
    languages: str = Query("en", description="Lista de códigos de idioma separados por comas"),
    format: str = Query("json", regex="^(json|srt)$", description="Formato de respuesta: json o srt"),
):
    """
    Endpoint principal para obtener la transcripción de un video.
    """
    langs = [lang.strip() for lang in languages.split(",") if lang.strip()]
    cache_key = f"transcript:{video_id}:{','.join(langs)}:{format}"

    # 1) Intentar obtener del caché de Redis
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            media_type = "application/json" if format == "json" else "text/plain"
            return PlainTextResponse(content=cached, media_type=media_type)
    except Exception as e:
        # Si Redis falla, se registra el error pero se continúa para no detener el servicio.
        print(f"Error al acceder a Redis: {e}")


    # 2) Si no está en caché, obtener de la API de YouTube
    try:
        transcript_data = get_transcript_list(video_id, langs)
    except TranscriptsDisabled:
        raise HTTPException(status_code=404, detail="Las transcripciones están deshabilitadas para este video.")
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No se encontró una transcripción para el video y los idiomas dados.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 3) Formatear y guardar en caché
    if format == "json":
        response_content = json.dumps(transcript_data, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        response_content = to_srt(transcript_data)
        media_type = "text/plain"

    try:
        await redis_client.setex(cache_key, REDIS_CACHE_TTL, response_content)
    except Exception as e:
        # Si Redis falla al guardar, se registra el error pero se devuelve la respuesta igualmente.
        print(f"Error al guardar en Redis: {e}")

    return PlainTextResponse(content=response_content, media_type=media_type)


@app.get("/transcript/languages")
async def available_languages(video_id: str):
    """
    Endpoint para obtener los idiomas de subtítulos disponibles para un video.
    """
    try:
        langs = get_available_languages(video_id)
        return JSONResponse(content={"video_id": video_id, "available_languages": langs})
    except TranscriptsDisabled:
        raise HTTPException(status_code=404, detail="Las transcripciones están deshabilitadas para este video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento que se ejecuta al apagar la aplicación para cerrar la conexión a Redis de forma segura.
    """
    await redis_client.close()