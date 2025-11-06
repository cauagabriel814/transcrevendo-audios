import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger():
    """
    Configura o sistema de logging para salvar em arquivo e console
    """
    # Criar diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Nome do arquivo com data
    log_filename = log_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log"

    # Formato dos logs
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Logger principal
    logger = logging.getLogger("audio_transcription")
    logger.setLevel(logging.INFO)

    # Handler para arquivo
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    # Adicionar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Instância do logger
logger = setup_logger()
