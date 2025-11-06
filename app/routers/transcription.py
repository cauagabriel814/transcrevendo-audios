from fastapi import APIRouter, Depends, File, UploadFile, status
from app.models.schemas import TranscriptionResponse, ErrorResponse, AudioBase64Request
from app.services.transcription_service import transcription_service
from app.core.security import verify_token

router = APIRouter(
    prefix="/transcription",
    tags=["Transcrição"]
)


@router.post(
    "/",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcrever Áudio",
    description="Envia um arquivo de áudio para transcrição usando OpenAI Whisper. Arquivos WAV maiores que 25MB são automaticamente comprimidos.",
    responses={
        200: {"description": "Áudio transcrito com sucesso"},
        400: {"model": ErrorResponse, "description": "Formato de arquivo inválido"},
        401: {"model": ErrorResponse, "description": "Token inválido ou expirado"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande mesmo após compressão"},
        500: {"model": ErrorResponse, "description": "Erro ao processar transcrição"}
    }
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Arquivo de áudio (mp3, wav, m4a, etc.)"),
    token_data: dict = Depends(verify_token)
) -> TranscriptionResponse:
    """
    Endpoint para transcrever arquivos de áudio

    - **file**: Arquivo de áudio para transcrição
    - **Authorization**: Bearer token JWT (obrigatório no header)

    Formatos aceitos: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
    Limite de tamanho: 25MB (50MB para WAV com compressão automática)

    **Compressão automática (apenas WAV):** Arquivos WAV maiores que 25MB são automaticamente convertidos para mono e reduzidos para 16kHz.
    """
    # Transcrever o áudio
    result = await transcription_service.transcribe_audio(file)

    return TranscriptionResponse(
        text=result["text"],
        language=result["language"],
        duration=result["duration"],
        compressed=result.get("compressed", False)
    )


@router.post(
    "/base64",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcrever Áudio (Base64)",
    description="Envia um áudio codificado em base64 para transcrição usando OpenAI Whisper. Arquivos WAV maiores que 25MB são automaticamente comprimidos.",
    responses={
        200: {"description": "Áudio transcrito com sucesso"},
        400: {"model": ErrorResponse, "description": "Formato de arquivo inválido ou base64 inválido"},
        401: {"model": ErrorResponse, "description": "Token inválido ou expirado"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande mesmo após compressão"},
        500: {"model": ErrorResponse, "description": "Erro ao processar transcrição"}
    }
)
async def transcribe_audio_base64(
    request: AudioBase64Request,
    token_data: dict = Depends(verify_token)
) -> TranscriptionResponse:
    """
    Endpoint para transcrever áudios enviados em base64

    - **audio_base64**: String base64 do áudio
    - **filename**: Nome do arquivo com extensão (ex: audio.mp3)
    - **Authorization**: Bearer token JWT (obrigatório no header)

    Formatos aceitos: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
    Limite de tamanho: 25MB (50MB para WAV com compressão automática)

    **Compressão automática (apenas WAV):** Arquivos WAV maiores que 25MB são automaticamente convertidos para mono e reduzidos para 16kHz.
    """
    # Transcrever o áudio
    result = await transcription_service.transcribe_audio_base64(
        request.audio_base64,
        request.filename
    )

    return TranscriptionResponse(
        text=result["text"],
        language=result["language"],
        duration=result["duration"],
        compressed=result.get("compressed", False)
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verifica se o serviço de transcrição está funcionando"
)
async def health_check():
    """
    Endpoint para verificar a saúde do serviço
    """
    return {
        "status": "healthy",
        "service": "transcription"
    }
