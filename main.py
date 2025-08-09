# main.py (v5.0 - Versión de Depuración Mínima)
# Se han eliminado todas las dependencias y código no esencial para aislar el problema.
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- Habilitar CORS ---
# Se mantiene la configuración de CORS para permitir la conexión desde el frontend.
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


@app.get("/")
def read_root():
    """
    Endpoint raíz para verificar la versión del despliegue.
    """
    return {
        "status": "ok",
        "version": "5.0"  # Nueva versión para confirmar el despliegue
    }


@app.get("/transcript/languages")
async def available_languages(video_id: str):
    """
    Endpoint simulado con la mínima lógica posible.
    Si esto funciona, el problema está en una de las dependencias eliminadas (Redis, etc.).
    """
    print(f"LOG: Solicitud recibida en /languages (VERSIÓN MÍNIMA) para video_id: {video_id}")
    
    # Se devuelve una respuesta falsa y simple.
    fake_languages = ["es-MINIMAL-OK", "en-MINIMAL-OK"]
    
    print(f"LOG: Devolviendo respuesta simulada mínima: {fake_languages}")
    
    return JSONResponse(content={"video_id": video_id, "available_languages": fake_languages})