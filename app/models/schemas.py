from pydantic import BaseModel, Field
from typing import Optional


class TokenRequest(BaseModel):
    """
    Modelo para requisição de token
    """
    username: str = Field(..., description="Nome de usuário")
    password: str = Field(..., description="Senha do usuário")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "admin",
                    "password": "senha_secreta"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Modelo para resposta com token
    """
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int


class TranscriptionResponse(BaseModel):
    """
    Modelo para resposta de transcrição
    """
    text: str = Field(..., description="Texto transcrito do áudio")
    language: Optional[str] = Field(None, description="Idioma detectado")
    duration: Optional[float] = Field(None, description="Duração do processamento em segundos")
    compressed: Optional[bool] = Field(False, description="Indica se o áudio foi comprimido automaticamente")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Este é o texto transcrito do áudio",
                    "language": "pt",
                    "duration": 2.5,
                    "compressed": False
                }
            ]
        }
    }


class AudioBase64Request(BaseModel):
    """
    Modelo para requisição de transcrição com áudio em base64
    """
    audio_base64: str = Field(..., description="Áudio codificado em base64")
    filename: str = Field(..., description="Nome do arquivo com extensão (ex: audio.mp3)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "audio_base64": "SGVsbG8gV29ybGQh...",
                    "filename": "audio.mp3"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Modelo para resposta de erro
    """
    detail: str
