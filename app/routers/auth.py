from fastapi import APIRouter, HTTPException, status
from app.models.schemas import TokenRequest, TokenResponse
from app.core.security import create_access_token
from app.core.config import settings
from app.core.logger import logger

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar Token JWT",
    description="Gera um token JWT válido por 3 horas para autenticação nas requisições"
)
async def generate_token(token_request: TokenRequest) -> TokenResponse:
    """
    Endpoint para gerar token JWT

    - **username**: Nome de usuário admin
    - **password**: Senha do usuário admin
    """
    # Validar credenciais do admin
    if token_request.username != settings.ADMIN_USERNAME or token_request.password != settings.ADMIN_PASSWORD:
        logger.warning(f"Tentativa de login falhou para usuário: {token_request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log de login bem-sucedido
    logger.info(f"Login bem-sucedido para usuário: {token_request.username}")

    # Criar token JWT com o username
    access_token = create_access_token(
        data={"sub": token_request.username}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_hours=settings.ACCESS_TOKEN_EXPIRE_HOURS
    )
