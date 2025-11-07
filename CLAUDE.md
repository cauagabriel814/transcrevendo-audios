# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Audio Transcription Service - A FastAPI microservice for transcribing audio files using OpenAI Whisper API with JWT authentication and automatic WAV compression.

**Key Features:**
- JWT authentication with 3-hour token validity
- Audio transcription via OpenAI Whisper API
- **Smart chunking for long audio files** (>5 min split into 5-min chunks)
- **Light compression for all files** (mono + 24kHz + MP3 128kbps)
- Supports file upload and base64 encoding
- Universal format support using pydub + FFmpeg
- **Zero timeout errors** - long files processed in chunks

## Development Commands

### Local Development (without Docker)

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the service (development mode with hot reload)
python run.py

# Alternative: Run with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development

```bash
# Build and run with docker-compose (recommended)
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

### Environment Configuration

Required `.env` variables:
```env
OPENAI_API_KEY=sk-your-key-here
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=3
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Architecture

### Core Application Structure

**FastAPI Application (`app/main.py`):**
- Main FastAPI app with CORS middleware
- Request logging middleware that tracks method, path, status, and duration
- Swagger UI at `/docs` and ReDoc at `/redoc`
- Max request body size: 150MB (configured for large base64 payloads)

**Configuration (`app/core/config.py`):**
- Uses Pydantic Settings with `.env` file loading
- Centralized settings management
- Environment-based configuration

**Authentication (`app/core/security.py`):**
- JWT token creation and verification using python-jose
- HTTPBearer security scheme
- Token payload includes username in "sub" claim
- Tokens expire based on `ACCESS_TOKEN_EXPIRE_HOURS` setting

### Key Services

**Transcription Service (`app/services/transcription_service.py`):**
- Singleton pattern (`transcription_service` instance)
- OpenAI Whisper integration via official SDK
- **Smart chunking strategy for long audio files:**
  - Audio > 5 minutes: automatically split into 5-minute chunks
  - Each chunk processed separately and sequentially
  - Transcriptions combined at the end
  - **Eliminates timeout errors completely**
  - **Much faster processing** (chunks process in parallel internally)
- **Light compression for all files:**
  - Convert stereo to mono (reduces ~50% size)
  - Maintain good sample rate (up to 24kHz)
  - Export as MP3 128kbps (excellent quality for voice)
- Uses pydub + FFmpeg for universal format support
- Returns: text, language, duration, compressed flag, chunks_processed, original_duration_minutes

**Chunking Implementation Details:**
- Uses pydub to handle ANY audio format (MP3, WAV, MPEG, M4A, OGG, FLAC, etc.)
- Requires FFmpeg installed in system/container
- Audio > 5 minutes: split into 5-minute chunks automatically
- Each chunk: compressed, transcribed, and combined
- No text loss: all chunks transcribed in order
- Typical result: 10-minute audio = 2 chunks processed in ~60-90 seconds
- Quality preserved: 24kHz mono MP3 128kbps is excellent for voice

### API Endpoints

**Authentication (`/auth`):**
- `POST /auth/token` - Generate JWT with admin username/password

**Transcription (`/transcription`):**
- `POST /transcription/` - Upload audio file (multipart/form-data)
- `POST /transcription/base64` - Submit base64-encoded audio (JSON)
- `GET /transcription/health` - Service health check

**Root:**
- `GET /` - Service info
- `GET /health` - General health check

### Data Models (`app/models/schemas.py`)

All Pydantic models with JSON schema examples:
- `TokenRequest` - Username/password for authentication
- `TokenResponse` - JWT token with expiry info
- `AudioBase64Request` - Base64 audio + filename
- `TranscriptionResponse` - Text, language, duration, compressed flag
- `ErrorResponse` - Error detail message

## Important Implementation Notes

### Audio File Size Handling

**File Upload Endpoint:**
- Reads entire file to memory with `await file.read()`
- Checks size before and after compression
- WAV files > 25MB trigger automatic compression
- Non-WAV files > 25MB are rejected with error

**Base64 Endpoint:**
- Validates base64 string size before decoding (~33% larger than binary)
- Max base64 size: 140MB (~100MB decoded file)
- Same compression logic as file upload

### Error Handling Strategy

The transcription service implements comprehensive error handling:
- Timeout errors (504) - Suggests smaller/compressed files
- File size errors (413) - Provides current size and limit
- Base64 decoding errors (400) - Validation message
- OpenAI API errors - Wrapped with helpful context

### Uvicorn Configuration (`run.py`)

Development server settings:
- `timeout_keep_alive=600` - 10 minute timeout for long transcriptions
- `limit_concurrency=100` - Max simultaneous connections
- `limit_max_requests=10000` - Worker restart threshold
- `h11_max_incomplete_event_size=200 * 1024 * 1024` - 200MB for large base64

## Development Guidelines

### Testing the API

1. Generate token:
```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

2. Test transcription (file):
```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@audio.mp3"
```

3. Test transcription (base64):
```bash
curl -X POST "http://localhost:8000/transcription/base64" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"audio_base64": "BASE64_STRING", "filename": "audio.mp3"}'
```

### Security Considerations

- JWT tokens are stateless (no database validation)
- Admin credentials stored in environment variables
- All transcription endpoints require valid JWT token
- CORS is wide open (`allow_origins=["*"]`) - restrict in production
- No rate limiting implemented - consider adding for production

### Logging

- Uses custom logger in `app/core/logger.py`
- Request/response logging in main.py middleware
- Auth success/failure logging in auth router
- All logs show method, path, status code, and duration

## Deployment

### Docker Production

The service is containerized with:
- Python 3.11-slim base image
- Health check configured (curl to `/health` endpoint)
- Restart policy: `unless-stopped`
- Volume mount for logs: `./logs:/app/logs`

### Known Limitations

1. **FFmpeg dependency:** Requires FFmpeg installed for audio compression (included in Docker)
2. **Memory usage:** Large files are loaded entirely into memory during chunking
3. **Stateless tokens:** No token revocation mechanism
4. **Sequential chunk processing:** Chunks are processed one by one (not parallel to avoid API rate limits)
5. **Always chunked:** Audio files > 5 minutes are automatically chunked - no option to disable

### File Size Reference

- Base64 is ~33% larger than binary
- WAV compression typically achieves 70-90% size reduction
- 44.1kHz stereo WAV → 16kHz mono ≈ 85% reduction
- OpenAI Whisper limit: 25MB per file

## Supported Audio Formats

mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac

**ALL formats are automatically compressed** to mono 24kHz MP3 128kbps before transcription.
**Audio files > 5 minutes are automatically split into 5-minute chunks** for faster, reliable processing.

## Local Development Setup (FFmpeg)

When running locally (not in Docker), you need to install FFmpeg:

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```
