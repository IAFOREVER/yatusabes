import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

# Se comenta la importación real para asegurarnos de no usarla en la prueba
# from transcript import get_transcript_list, to_srt, get_available_languages
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
    """
    return {
        "status": "ok",
        "message": "API de transcripciones funcionando",
        "version": "4.0"  # Nueva versión para confirmar despliegue
    }


@app.get("/test")
def test_endpoint():
    """
    Este endpoint simple nos ayuda a verificar si el ruteo de FastAPI funciona.
    """
    print("LOG: El endpoint /test fue alcanzado con éxito.")
    return {"message": "Test endpoint is working!"}


# --- MODIFICACIÓN CLAVE ---
@app.get("/transcript/languages")
async def available_languages(video_id: str):
    """
    Endpoint modificado para devolver una respuesta simulada (mock).
    Esto nos permite probar si el resto del flujo funciona correctamente.
    """
    print(f"LOG: Solicitud recibida en /languages (VERSIÓN SIMULADA) para video_id: {video_id}")
    
    # En lugar de llamar a la API de YouTube, devolvemos datos falsos.
    fake_languages = ["es-FAKE", "en-FAKE", "fr-FAKE"]
    
    print(f"LOG: Devolviendo respuesta simulada: {fake_languages}")
    
    return JSONResponse(content={"video_id": video_id, "available_languages": fake_languages})


# Se deja el endpoint original comentado por ahora
# @app.get("/transcript")
# async def transcript(...):
#     ...


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()