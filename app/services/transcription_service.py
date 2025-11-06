import time
import base64
import io
import wave
import numpy as np
from openai import OpenAI
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings


class TranscriptionService:
    """
    Serviço para transcrição de áudios usando OpenAI Whisper
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.max_size = 25 * 1024 * 1024  # 25MB em bytes

    def _compress_audio_wav(self, audio_bytes: bytes, filename: str) -> tuple[bytes, str]:
        """
        Comprime um arquivo de áudio WAV usando numpy
        Converte para mono e reduz sample rate para 16kHz

        Args:
            audio_bytes: Bytes do áudio WAV
            filename: Nome do arquivo original

        Returns:
            tuple: (bytes comprimidos, novo filename)
        """
        try:
            # Ler o arquivo WAV
            input_wav = io.BytesIO(audio_bytes)
            with wave.open(input_wav, 'rb') as wav_in:
                # Obter parâmetros do áudio
                channels = wav_in.getnchannels()
                sampwidth = wav_in.getsampwidth()
                framerate = wav_in.getframerate()
                n_frames = wav_in.getnframes()
                frames = wav_in.readframes(n_frames)

            # Converter bytes para numpy array baseado no sample width
            if sampwidth == 1:  # 8-bit
                dtype = np.uint8
            elif sampwidth == 2:  # 16-bit
                dtype = np.int16
            elif sampwidth == 4:  # 32-bit
                dtype = np.int32
            else:
                raise ValueError(f"Sample width não suportado: {sampwidth}")

            # Converter frames para array numpy
            audio_array = np.frombuffer(frames, dtype=dtype)

            # Converter para mono se for stereo
            if channels == 2:
                # Reshape para separar canais e calcular média
                audio_array = audio_array.reshape(-1, 2)
                audio_array = audio_array.mean(axis=1).astype(dtype)
                channels = 1

            # Reduzir sample rate para 16kHz (ideal para voz)
            target_rate = 16000
            if framerate > target_rate:
                # Calcular taxa de redução
                ratio = framerate / target_rate
                # Fazer downsampling simples pegando 1 a cada N samples
                indices = np.arange(0, len(audio_array), ratio).astype(int)
                audio_array = audio_array[indices]
                framerate = target_rate

            # Converter array de volta para bytes
            frames = audio_array.tobytes()

            # Criar novo arquivo WAV em memória
            output_wav = io.BytesIO()
            with wave.open(output_wav, 'wb') as wav_out:
                wav_out.setnchannels(channels)
                wav_out.setsampwidth(sampwidth)
                wav_out.setframerate(framerate)
                wav_out.writeframes(frames)

            compressed_bytes = output_wav.getvalue()
            return compressed_bytes, filename

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao comprimir áudio WAV: {str(e)}"
            )

    async def transcribe_audio(self, file: UploadFile) -> dict:
        """
        Transcreve um arquivo de áudio usando o modelo Whisper da OpenAI
        Se o arquivo for maior que 25MB, será automaticamente comprimido

        Args:
            file: Arquivo de áudio enviado

        Returns:
            dict: Dicionário contendo o texto transcrito, idioma, duração e se foi comprimido

        Raises:
            HTTPException: Se houver erro na transcrição
        """
        # Validar formato do arquivo
        allowed_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "flac"]
        file_extension = file.filename.split(".")[-1].lower() if file.filename else ""

        if file_extension not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de arquivo não suportado. Formatos aceitos: {', '.join(allowed_formats)}"
            )

        # Ler o arquivo
        audio_bytes = await file.read()
        file_size = len(audio_bytes)
        filename = file.filename or f"audio.{file_extension}"

        compressed = False

        # Se o arquivo for maior que 25MB, tentar comprimir
        if file_size > self.max_size:
            # Só conseguimos comprimir WAV com Python puro
            if file_extension == "wav":
                compressed = True
                original_size = file_size
                audio_bytes, filename = self._compress_audio_wav(audio_bytes, filename)
                file_size = len(audio_bytes)

                # Verificar se ainda está muito grande após compressão
                if file_size > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Arquivo WAV muito grande mesmo após compressão. Original: {original_size / (1024 * 1024):.2f}MB, Comprimido: {file_size / (1024 * 1024):.2f}MB. Limite: 25MB"
                    )
            else:
                # Para outros formatos, retornar erro explicativo
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Arquivo muito grande: {file_size / (1024 * 1024):.2f}MB. Limite: 25MB. Para arquivos maiores, use formato WAV que possui compressão automática."
                )

        try:
            start_time = time.time()

            # Criar objeto de arquivo em memória
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            # Transcrever o áudio usando Whisper
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

            duration = time.time() - start_time

            return {
                "text": transcript.text,
                "language": getattr(transcript, "language", None),
                "duration": round(duration, 2),
                "compressed": compressed
            }

        except Exception as e:
            # Melhorar mensagem de erro para problemas comuns
            error_message = str(e)

            # Detectar erros de timeout
            if "timeout" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Timeout ao processar áudio. O arquivo pode ser muito grande ou complexo. Tente com um arquivo menor ou em formato mais comprimido."
                )

            # Detectar erros de tamanho da API OpenAI
            if "file size" in error_message.lower() or "too large" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Arquivo rejeitado pela API OpenAI (limite de 25MB). Tamanho atual: {file_size / (1024 * 1024):.2f}MB. Comprima o arquivo antes de enviar."
                )

            # Erro genérico
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao transcrever áudio: {error_message}"
            )

    async def transcribe_audio_base64(self, audio_base64: str, filename: str) -> dict:
        """
        Transcreve um arquivo de áudio a partir de uma string base64
        Se o arquivo for maior que 25MB, será automaticamente comprimido

        Args:
            audio_base64: String base64 do áudio
            filename: Nome do arquivo com extensão

        Returns:
            dict: Dicionário contendo o texto transcrito, idioma, duração e se foi comprimido

        Raises:
            HTTPException: Se houver erro na transcrição
        """
        # Validar formato do arquivo
        allowed_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "flac"]
        file_extension = filename.split(".")[-1].lower() if filename else ""

        if file_extension not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de arquivo não suportado. Formatos aceitos: {', '.join(allowed_formats)}"
            )

        # Validar tamanho do base64 antes de decodificar
        # Base64 é aproximadamente 33% maior que o arquivo binário
        base64_size = len(audio_base64)
        estimated_file_size = (base64_size * 3) / 4

        # Limite máximo mais generoso para base64 (aproximadamente 100MB decodificado)
        max_base64_size = 140 * 1024 * 1024  # ~140MB base64 = ~100MB arquivo

        if base64_size > max_base64_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"String base64 muito grande: {base64_size / (1024 * 1024):.2f}MB (tamanho estimado do arquivo: {estimated_file_size / (1024 * 1024):.2f}MB). Limite máximo: {max_base64_size / (1024 * 1024):.2f}MB base64."
            )

        try:
            # Decodificar base64
            audio_bytes = base64.b64decode(audio_base64, validate=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao decodificar base64: {str(e)}. Verifique se a string está corretamente codificada em base64."
            )

        file_size = len(audio_bytes)
        compressed = False

        # Se o arquivo for maior que 25MB, tentar comprimir
        if file_size > self.max_size:
            # Só conseguimos comprimir WAV com Python puro
            if file_extension == "wav":
                compressed = True
                original_size = file_size
                audio_bytes, filename = self._compress_audio_wav(audio_bytes, filename)
                file_size = len(audio_bytes)

                # Verificar se ainda está muito grande após compressão
                if file_size > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Arquivo WAV muito grande mesmo após compressão. Original: {original_size / (1024 * 1024):.2f}MB, Comprimido: {file_size / (1024 * 1024):.2f}MB. Limite: 25MB. Considere usar um formato mais comprimido como MP3."
                    )
            else:
                # Para outros formatos, retornar erro explicativo
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Arquivo muito grande: {file_size / (1024 * 1024):.2f}MB. Limite: 25MB. Formatos recomendados para arquivos grandes: MP3 (com bitrate baixo) ou WAV (com compressão automática). Considere comprimir o arquivo antes de enviá-lo."
                )

        try:
            start_time = time.time()

            # Criar um objeto de arquivo em memória
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            # Transcrever o áudio usando Whisper
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

            duration = time.time() - start_time

            return {
                "text": transcript.text,
                "language": getattr(transcript, "language", None),
                "duration": round(duration, 2),
                "compressed": compressed
            }

        except Exception as e:
            # Melhorar mensagem de erro para problemas comuns
            error_message = str(e)

            # Detectar erros de timeout
            if "timeout" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Timeout ao processar áudio. O arquivo pode ser muito grande ou complexo. Tente com um arquivo menor ou em formato mais comprimido."
                )

            # Detectar erros de tamanho da API OpenAI
            if "file size" in error_message.lower() or "too large" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Arquivo rejeitado pela API OpenAI (limite de 25MB). Tamanho atual: {file_size / (1024 * 1024):.2f}MB. Comprima o arquivo antes de enviar."
                )

            # Erro genérico
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao transcrever áudio: {error_message}"
            )


# Instância singleton do serviço
transcription_service = TranscriptionService()
