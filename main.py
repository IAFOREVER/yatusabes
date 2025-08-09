import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
import redis.asyncio as redis
from fastapi.staticfiles import StaticFiles

from transcript import get_transcript_list, to_srt, get_available_languages
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound

app = FastAPI()

@app.get("/transcript")
async def transcript(
    video_id: str,
    languages: str = Query("en", description="Comma separated list of language codes"),
    format: str = Query("json", regex="^(json|srt)$", description="Response format: json or srt"),
):
    langs = [lang.strip() for lang in languages.split(",") if lang.strip()]
    cache_key = f"transcript:{video_id}:{','.join(langs)}:{format}"

    # 1) Intentar obtener del cache
    cached = await redis_client.get(cache_key)
    if cached:
        if format == "json":
            return PlainTextResponse(content=cached, media_type="application/json")
        else:
            return PlainTextResponse(content=cached, media_type="text/plain")

    # 2) Obtener del API
    try:
        transcript_data = get_transcript_list(video_id, langs)
    except TranscriptsDisabled:
        raise HTTPException(status_code=404, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript found for the given video and languages.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 3) Formatear y guardar en cache
    if format == "json":
        json_str = json.dumps(transcript_data, indent=2, ensure_ascii=False)
        await redis_client.setex(cache_key, REDIS_CACHE_TTL, json_str)
        return PlainTextResponse(content=json_str, media_type="application/json")
    else:
        srt_text = to_srt(transcript_data)
        await redis_client.setex(cache_key, REDIS_CACHE_TTL, srt_text)
        return PlainTextResponse(content=srt_text, media_type="text/plain")

@app.get("/transcript/languages")
async def available_languages(video_id: str):
    try:
        langs = get_available_languages(video_id)
        return JSONResponse(content={"video_id": video_id, "available_languages": langs})
    except TranscriptsDisabled:
        raise HTTPException(status_code=404, detail="Transcripts are disabled for this video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()

    # Montar carpeta estática
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Configuración Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", 3600))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)