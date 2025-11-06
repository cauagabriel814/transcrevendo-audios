from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import logger
from app.routers import auth, transcription
import time

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    ## Microserviço de Transcrição de Áudio

    Este serviço permite:
    * **Gerar tokens JWT** com validade de 3 horas
    * **Transcrever áudios grandes** usando OpenAI Whisper
    * **Suporte a múltiplos formatos** de áudio (mp3, wav, m4a, etc.)

    ### Como usar:
    1. Obtenha um token JWT no endpoint `/auth/token`
    2. Use o token no header `Authorization: Bearer {token}`
    3. Envie o áudio para `/transcription/`
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origins permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log da requisição
    logger.info(f"Request: {request.method} {request.url.path}")

    # Processar requisição
    response = await call_next(request)

    # Calcular tempo de processamento
    process_time = time.time() - start_time

    # Log da resposta
    logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")

    return response


# Registrar routers
app.include_router(auth.router)
app.include_router(transcription.router)


# Log de inicialização
logger.info(f"Application started - {settings.API_TITLE} v{settings.API_VERSION}")


@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raiz com informações do serviço
    """
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/transcription/health"
    }


@app.get("/health", tags=["Root"])
async def health():
    """
    Health check geral da aplicação
    """
    return {
        "status": "healthy",
        "service": settings.API_TITLE
    }
