import time
import base64
import io
import wave
import numpy as np
import subprocess
import json as json_module
from openai import OpenAI
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from pydub import AudioSegment


class TranscriptionService:
    """
    Serviço para transcrição de áudios usando OpenAI Whisper
    """

    def __init__(self):
        # Configurar cliente OpenAI com timeout de 10 minutos (600 segundos)
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=600.0,  # 10 minutos para transcrições grandes
            max_retries=2
        )
        self.max_size = 25 * 1024 * 1024  # 25MB em bytes

    def _convert_to_mp3_ffmpeg(self, audio_bytes: bytes, filename: str) -> bytes:
        """
        Converte qualquer áudio para MP3 usando FFmpeg diretamente
        (Mais confiável que pydub para arquivos MPEG corrompidos)

        Args:
            audio_bytes: Bytes do áudio original
            filename: Nome do arquivo original

        Returns:
            Bytes do áudio convertido para MP3
        """
        try:
            import tempfile
            import os

            # Salvar arquivo original temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as tmp_input:
                tmp_input.write(audio_bytes)
                input_path = tmp_input.name

            # Criar arquivo de saída temporário
            output_path = input_path.replace(f".{filename.split('.')[-1]}", ".mp3")

            # Converter com FFmpeg
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-i', input_path,
                    '-vn',  # Sem vídeo
                    '-acodec', 'libmp3lame',  # Codec MP3
                    '-b:a', '128k',  # Bitrate 128kbps
                    '-ar', '24000',  # Sample rate 24kHz
                    '-ac', '1',  # Mono
                    '-y',  # Sobrescrever
                    output_path
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            # Ler o arquivo convertido
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    mp3_bytes = f.read()

                # Limpar arquivos temporários
                os.unlink(input_path)
                os.unlink(output_path)

                return mp3_bytes
            else:
                # Limpar em caso de erro
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)
                raise Exception(f"FFmpeg conversion failed: {result.stderr}")

        except Exception as e:
            print(f"Erro ao converter com FFmpeg: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao converter áudio: {str(e)}"
            )

    def _get_audio_duration_ffprobe(self, audio_bytes: bytes, filename: str) -> float:
        """
        Usa FFprobe para detectar a duração real do áudio
        (Mais confiável que pydub para arquivos MPEG)

        Args:
            audio_bytes: Bytes do áudio
            filename: Nome do arquivo

        Returns:
            Duração em segundos
        """
        try:
            # Salvar temporariamente para o FFprobe ler
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            # Usar FFprobe para obter a duração
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    tmp_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Limpar arquivo temporário
            import os
            os.unlink(tmp_path)

            if result.returncode == 0:
                data = json_module.loads(result.stdout)
                duration = float(data.get('format', {}).get('duration', 0))
                return duration
            else:
                return 0.0

        except Exception as e:
            print(f"Erro ao detectar duração com FFprobe: {e}")
            return 0.0

    def _split_audio_into_chunks(self, audio: AudioSegment, chunk_duration_minutes: int = 5) -> list[AudioSegment]:
        """
        Divide um áudio em chunks de duração específica

        Args:
            audio: AudioSegment para dividir
            chunk_duration_minutes: Duração de cada chunk em minutos

        Returns:
            Lista de AudioSegments (chunks)
        """
        chunk_duration_ms = chunk_duration_minutes * 60 * 1000  # Converter para milissegundos
        chunks = []

        for i in range(0, len(audio), chunk_duration_ms):
            chunk = audio[i:i + chunk_duration_ms]
            chunks.append(chunk)

        return chunks

    def _compress_audio_light(self, audio_bytes: bytes, filename: str) -> tuple[bytes, str, float]:
        """
        Comprime um arquivo de áudio de forma LEVE para reduzir tamanho mantendo qualidade

        Estratégia de compressão leve:
        - Converte para mono (1 canal)
        - Mantém sample rate original ou reduz levemente (max 24kHz)
        - Exporta como MP3 com bitrate 128kbps (boa qualidade)

        Args:
            audio_bytes: Bytes do áudio em qualquer formato
            filename: Nome do arquivo original

        Returns:
            tuple: (bytes comprimidos, novo filename, duração em segundos)
        """
        try:
            # Detectar formato do arquivo
            file_extension = filename.split(".")[-1].lower() if filename else "mp3"

            # Carregar o áudio usando pydub (suporta vários formatos)
            audio_file = io.BytesIO(audio_bytes)
            audio = AudioSegment.from_file(audio_file, format=file_extension)

            # Obter informações do áudio original
            original_channels = audio.channels
            original_frame_rate = audio.frame_rate
            duration_seconds = len(audio) / 1000.0

            # Aplicar compressão leve
            # 1. Converter para mono (se não for)
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # 2. Reduzir sample rate apenas se for muito alto (manter boa qualidade)
            if audio.frame_rate > 24000:
                audio = audio.set_frame_rate(24000)

            # 3. Exportar como MP3 com bitrate razoável (128kbps - boa qualidade)
            output_buffer = io.BytesIO()
            audio.export(
                output_buffer,
                format="mp3",
                bitrate="128k",
                parameters=["-ac", "1"]  # Garantir mono
            )

            compressed_bytes = output_buffer.getvalue()
            compressed_size = len(compressed_bytes)
            original_size = len(audio_bytes)
            reduction_percent = ((original_size - compressed_size) / original_size) * 100

            # Criar novo nome de arquivo com extensão .mp3
            base_filename = filename.rsplit(".", 1)[0] if "." in filename else filename
            new_filename = f"{base_filename}.mp3"

            print(f"Compressão leve aplicada:")
            print(f"  - Original: {original_channels} canais, {original_frame_rate}Hz, {original_size / (1024*1024):.2f}MB")
            print(f"  - Comprimido: 1 canal, {audio.frame_rate}Hz, {compressed_size / (1024*1024):.2f}MB")
            print(f"  - Redução: {reduction_percent:.1f}%")
            print(f"  - Duração: {duration_seconds:.1f}s")

            return compressed_bytes, new_filename, duration_seconds

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao comprimir áudio: {str(e)}. Certifique-se de que o FFmpeg está instalado."
            )

    def _process_audio_chunk(self, audio_chunk: AudioSegment, chunk_index: int) -> str:
        """
        Processa um chunk de áudio e retorna a transcrição

        Args:
            audio_chunk: AudioSegment do chunk
            chunk_index: Índice do chunk (para logging)

        Returns:
            Texto transcrito do chunk
        """
        try:
            # Exportar chunk como MP3
            output_buffer = io.BytesIO()
            audio_chunk.export(
                output_buffer,
                format="mp3",
                bitrate="128k",
                parameters=["-ac", "1", "-ar", "24000"]
            )

            chunk_bytes = output_buffer.getvalue()
            chunk_size_mb = len(chunk_bytes) / (1024 * 1024)

            print(f"Processando chunk {chunk_index + 1}: {chunk_size_mb:.2f}MB, {len(audio_chunk)/1000:.1f}s")

            # Criar objeto de arquivo em memória
            audio_file = io.BytesIO(chunk_bytes)
            audio_file.name = f"chunk_{chunk_index}.mp3"

            # Transcrever o chunk
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

            return transcript

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar chunk {chunk_index + 1}: {str(e)}"
            )

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
        original_size = len(audio_bytes)
        filename = file.filename or f"audio.{file_extension}"

        try:
            start_time = time.time()

            # Usar FFprobe para detectar duração (mais confiável para MPEG)
            duration_seconds_ffprobe = self._get_audio_duration_ffprobe(audio_bytes, filename)

            # Carregar o áudio com pydub
            audio_file_input = io.BytesIO(audio_bytes)
            audio = AudioSegment.from_file(audio_file_input, format=file_extension)

            # Usar a duração do FFprobe se disponível, senão usar do pydub
            if duration_seconds_ffprobe > 0:
                duration_seconds = duration_seconds_ffprobe
                print(f"[OK] Duracao detectada via FFprobe: {duration_seconds:.1f}s")

                # Se FFprobe detectou duração muito diferente de pydub, converter para MP3 primeiro
                pydub_duration = len(audio) / 1000.0
                if abs(duration_seconds - pydub_duration) > 60:  # Diferença > 1 minuto
                    print(f"[AVISO] Pydub detectou apenas {pydub_duration:.1f}s (problema de leitura MPEG)")
                    print(f"[Convertendo] Converting to MP3 using FFmpeg directly...")

                    # Converter para MP3 usando FFmpeg diretamente (mais confiável)
                    mp3_bytes = self._convert_to_mp3_ffmpeg(audio_bytes, filename)
                    print(f"[OK] Conversao FFmpeg completa. Tamanho MP3: {len(mp3_bytes)/(1024*1024):.2f}MB")

                    # Recarregar o áudio convertido
                    audio_file_input = io.BytesIO(mp3_bytes)
                    audio = AudioSegment.from_file(audio_file_input, format="mp3")
                    print(f"[OK] MP3 carregado. Duracao detectada: {len(audio)/1000.0:.1f}s ({len(audio)/1000.0/60:.1f} min)")
            else:
                duration_seconds = len(audio) / 1000.0
                print(f"[AVISO] Duracao detectada via pydub: {duration_seconds:.1f}s")

            duration_minutes = duration_seconds / 60.0

            print(f"\n{'='*60}")
            print(f"Arquivo recebido: {filename}")
            print(f"Tamanho original: {original_size / (1024*1024):.2f}MB")
            print(f"Duração: {duration_minutes:.1f} minutos ({duration_seconds:.1f}s)")
            print(f"{'='*60}\n")

            # Decidir estratégia baseado na duração
            # Se for > 5 minutos, dividir em chunks
            if duration_minutes > 5:
                print(f"[AVISO] Audio longo detectado! Dividindo em chunks de 5 minutos...")

                # Dividir em chunks de 5 minutos
                chunks = self._split_audio_into_chunks(audio, chunk_duration_minutes=5)
                print(f"[OK] Audio dividido em {len(chunks)} chunks\n")

                # Transcrever cada chunk
                transcriptions = []
                for i, chunk in enumerate(chunks):
                    chunk_start_time = time.time()
                    chunk_text = self._process_audio_chunk(chunk, i)
                    chunk_duration = time.time() - chunk_start_time
                    transcriptions.append(chunk_text)
                    print(f"[OK] Chunk {i+1}/{len(chunks)} transcrito em {chunk_duration:.1f}s\n")

                # Juntar todas as transcrições
                full_text = " ".join(transcriptions)
                total_duration = time.time() - start_time

                print(f"\n{'='*60}")
                print(f"[OK] Transcricao completa!")
                print(f"Tempo total: {total_duration:.1f}s")
                print(f"Chunks processados: {len(chunks)}")
                print(f"{'='*60}\n")

                return {
                    "text": full_text,
                    "language": "pt",  # Detectado no primeiro chunk
                    "duration": round(total_duration, 2),
                    "compressed": True,
                    "chunks_processed": len(chunks),
                    "original_duration_minutes": round(duration_minutes, 1)
                }
            else:
                # Áudio curto (<=5 min), processar normalmente com compressão leve
                print(f"Áudio curto. Processando normalmente com compressão leve...")

                # Aplicar compressão leve
                compressed_bytes, compressed_filename, duration_sec = self._compress_audio_light(audio_bytes, filename)
                file_size = len(compressed_bytes)

                # Criar objeto de arquivo em memória
                audio_file = io.BytesIO(compressed_bytes)
                audio_file.name = compressed_filename

                # Transcrever o áudio usando Whisper
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

                total_duration = time.time() - start_time

                return {
                    "text": transcript.text,
                    "language": getattr(transcript, "language", None),
                    "duration": round(total_duration, 2),
                    "compressed": True
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

        original_size = len(audio_bytes)

        try:
            start_time = time.time()

            # Usar FFprobe para detectar duração (mais confiável para MPEG)
            duration_seconds_ffprobe = self._get_audio_duration_ffprobe(audio_bytes, filename)

            # Carregar o áudio com pydub
            audio_file_input = io.BytesIO(audio_bytes)
            audio = AudioSegment.from_file(audio_file_input, format=file_extension)

            # Usar a duração do FFprobe se disponível, senão usar do pydub
            if duration_seconds_ffprobe > 0:
                duration_seconds = duration_seconds_ffprobe
                print(f"[OK] Duracao detectada via FFprobe: {duration_seconds:.1f}s")

                # Se FFprobe detectou duração muito diferente de pydub, converter para MP3 primeiro
                pydub_duration = len(audio) / 1000.0
                if abs(duration_seconds - pydub_duration) > 60:  # Diferença > 1 minuto
                    print(f"[AVISO] Pydub detectou apenas {pydub_duration:.1f}s (problema de leitura MPEG)")
                    print(f"[Convertendo] Converting to MP3 using FFmpeg directly...")

                    # Converter para MP3 usando FFmpeg diretamente (mais confiável)
                    mp3_bytes = self._convert_to_mp3_ffmpeg(audio_bytes, filename)
                    print(f"[OK] Conversao FFmpeg completa. Tamanho MP3: {len(mp3_bytes)/(1024*1024):.2f}MB")

                    # Recarregar o áudio convertido
                    audio_file_input = io.BytesIO(mp3_bytes)
                    audio = AudioSegment.from_file(audio_file_input, format="mp3")
                    print(f"[OK] MP3 carregado. Duracao detectada: {len(audio)/1000.0:.1f}s ({len(audio)/1000.0/60:.1f} min)")
            else:
                duration_seconds = len(audio) / 1000.0
                print(f"[AVISO] Duracao detectada via pydub: {duration_seconds:.1f}s")

            duration_minutes = duration_seconds / 60.0

            print(f"\n{'='*60}")
            print(f"Arquivo recebido (base64): {filename}")
            print(f"Tamanho original: {original_size / (1024*1024):.2f}MB")
            print(f"Duração: {duration_minutes:.1f} minutos ({duration_seconds:.1f}s)")
            print(f"{'='*60}\n")

            # Decidir estratégia baseado na duração
            # Se for > 5 minutos, dividir em chunks
            if duration_minutes > 5:
                print(f"[AVISO] Audio longo detectado! Dividindo em chunks de 5 minutos...")

                # Dividir em chunks de 5 minutos
                chunks = self._split_audio_into_chunks(audio, chunk_duration_minutes=5)
                print(f"[OK] Audio dividido em {len(chunks)} chunks\n")

                # Transcrever cada chunk
                transcriptions = []
                for i, chunk in enumerate(chunks):
                    chunk_start_time = time.time()
                    chunk_text = self._process_audio_chunk(chunk, i)
                    chunk_duration = time.time() - chunk_start_time
                    transcriptions.append(chunk_text)
                    print(f"[OK] Chunk {i+1}/{len(chunks)} transcrito em {chunk_duration:.1f}s\n")

                # Juntar todas as transcrições
                full_text = " ".join(transcriptions)
                total_duration = time.time() - start_time

                print(f"\n{'='*60}")
                print(f"[OK] Transcricao completa!")
                print(f"Tempo total: {total_duration:.1f}s")
                print(f"Chunks processados: {len(chunks)}")
                print(f"{'='*60}\n")

                return {
                    "text": full_text,
                    "language": "pt",
                    "duration": round(total_duration, 2),
                    "compressed": True,
                    "chunks_processed": len(chunks),
                    "original_duration_minutes": round(duration_minutes, 1)
                }
            else:
                # Áudio curto (<=5 min), processar normalmente com compressão leve
                print(f"Áudio curto. Processando normalmente com compressão leve...")

                # Aplicar compressão leve
                compressed_bytes, compressed_filename, duration_sec = self._compress_audio_light(audio_bytes, filename)
                file_size = len(compressed_bytes)

                # Criar objeto de arquivo em memória
                audio_file = io.BytesIO(compressed_bytes)
                audio_file.name = compressed_filename

                # Transcrever o áudio usando Whisper
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

                total_duration = time.time() - start_time

                return {
                    "text": transcript.text,
                    "language": getattr(transcript, "language", None),
                    "duration": round(total_duration, 2),
                    "compressed": True
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
