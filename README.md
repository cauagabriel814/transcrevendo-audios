# Audio Transcription Service

Microserviço para transcrição de áudios usando OpenAI Whisper API com autenticação JWT e compressão automática para arquivos WAV.

> 🚀 **Quick Start:** Para começar rapidamente, veja [QUICK_START.md](QUICK_START.md)

## Funcionalidades

- ✅ Autenticação JWT com tokens válidos por 3 horas
- ✅ Transcrição de áudios usando OpenAI Whisper
- ✅ **Compressão automática** de arquivos WAV maiores que 25MB
- ✅ Suporte para upload via arquivo ou base64
- ✅ Suporte a múltiplos formatos (mp3, wav, m4a, ogg, flac, etc.)
- ✅ Validação de formato e tamanho de arquivo
- ✅ API documentada com Swagger UI
- ✅ **Sem dependências externas** (FFmpeg não necessário)

## Tecnologias

- FastAPI
- Uvicorn
- OpenAI Whisper API
- JWT (python-jose)
- Pydantic
- Python puro (wave + audioop para compressão)

## Instalação

### 1. Criar ambiente virtual

```bash
python -m venv venv
```

### 2. Ativar ambiente virtual

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Edite o arquivo `.env` e adicione suas credenciais:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here

# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=3
```

**Para gerar uma SECRET_KEY segura:**

```bash
openssl rand -hex 32
```

Ou em Python:
```python
import secrets
print(secrets.token_hex(32))
```

## Executar o serviço

### Opção 1: Usando Docker (Recomendado)

**1. Certifique-se que o Docker está instalado:**
```bash
docker --version
docker-compose --version
```

**2. Configure o arquivo .env com suas credenciais**

**3. Build e execute com docker-compose:**
```bash
docker-compose up --build
```

Ou execute em background:
```bash
docker-compose up -d
```

**4. Parar o serviço:**
```bash
docker-compose down
```

**Ver logs:**
```bash
docker-compose logs -f
```

### Opção 2: Usando Docker diretamente

```bash
# Build da imagem
docker build -t audio-transcription-api .

# Executar o container
docker run -d \
  --name audio-transcription-api \
  -p 8000:8000 \
  --env-file .env \
  audio-transcription-api
```

### Opção 3: Usando run.py (sem Docker)

```bash
python run.py
```

### Opção 4: Usando uvicorn diretamente (sem Docker)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O serviço estará disponível em: `http://localhost:8000`

## Documentação da API

Acesse a documentação interativa:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Como usar

### 1. Gerar token JWT

**Requisição:**
```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_hours": 3
}
```

### 2. Transcrever áudio (via arquivo)

**Requisição:**
```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@/path/to/audio.mp3"
```

**Resposta:**
```json
{
  "text": "Texto transcrito do áudio",
  "language": "pt",
  "duration": 2.5,
  "compressed": false
}
```

### 3. Transcrever áudio (via base64)

**Requisição:**
```bash
curl -X POST "http://localhost:8000/transcription/base64" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "SGVsbG8gV29ybGQh...",
    "filename": "audio.mp3"
  }'
```

**Resposta:**
```json
{
  "text": "Texto transcrito do áudio",
  "language": "pt",
  "duration": 2.5,
  "compressed": true
}
```

## Compressão Automática de Áudio

### Como funciona?

O serviço usa **apenas bibliotecas Python nativas** (wave + audioop) para comprimir arquivos WAV maiores que 25MB:

**Estratégia de compressão:**
1. **Converter para mono** (se for stereo) - reduz ~50% do tamanho
2. **Reduzir sample rate para 16kHz** - ideal para transcrição de voz

### Limites de tamanho

- **MP3, M4A, OGG, FLAC, etc:** Máximo 25MB
- **WAV:** Máximo ~50MB (comprimido automaticamente para < 25MB)

### Vantagens

- ✅ **Sem dependências externas** - não precisa instalar FFmpeg
- ✅ **Rápido** - compressão em memória usando bibliotecas nativas
- ✅ **Transparente** - usuário só envia o arquivo
- ✅ **Qualidade preservada** - 16kHz mono é suficiente para transcrição
- ✅ **Feedback** - resposta indica se foi comprimido (`compressed: true`)

### Exemplo

```python
# Enviar um arquivo WAV stereo 44.1kHz de 50MB
# Serviço comprime para: mono 16kHz ~12MB
# Resposta: {"text": "...", "compressed": true, ...}
```

## Formatos de áudio suportados

- mp3 (até 25MB)
- mp4 (até 25MB)
- mpeg (até 25MB)
- mpga (até 25MB)
- m4a (até 25MB)
- **wav (até 50MB com compressão automática)**
- webm (até 25MB)
- ogg (até 25MB)
- flac (até 25MB)

**Recomendação:** Para arquivos grandes (> 25MB), use formato WAV que possui compressão automática.

## Estrutura do projeto

```
residire-treatment-audio/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação principal
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configurações
│   │   └── security.py      # Autenticação JWT
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Modelos Pydantic
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints de autenticação
│   │   └── transcription.py # Endpoints de transcrição
│   └── services/
│       ├── __init__.py
│       └── transcription_service.py  # Serviço OpenAI + compressão
├── .env                     # Variáveis de ambiente
├── .gitignore
├── .dockerignore
├── Dockerfile               # Configuração Docker
├── docker-compose.yml       # Docker Compose
├── requirements.txt
├── run.py                   # Script para executar
├── README.md
├── DOCKER.md                # Guia completo Docker
└── examples.http            # Exemplos de requisições
```

## Endpoints

### Autenticação

- `POST /auth/token` - Gerar token JWT

### Transcrição

- `POST /transcription/` - Transcrever áudio via arquivo (requer autenticação)
- `POST /transcription/base64` - Transcrever áudio via base64 (requer autenticação)
- `GET /transcription/health` - Health check do serviço

### Root

- `GET /` - Informações do serviço
- `GET /health` - Health check geral

## Códigos de resposta

- `200` - Sucesso
- `400` - Formato de arquivo inválido ou base64 inválido
- `401` - Token inválido ou expirado
- `413` - Arquivo muito grande (> 25MB para formatos não-WAV, > 50MB para WAV)
- `500` - Erro interno no servidor

## Exemplo de integração

### Python

```python
import requests
import base64

# 1. Obter token
token_response = requests.post(
    "http://localhost:8000/auth/token",
    json={"user_id": "user123"}
)
token = token_response.json()["access_token"]

# 2. Transcrever áudio (via arquivo)
with open("audio.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcription/",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )
    print(response.json()["text"])

# 3. Transcrever áudio WAV grande (50MB - será comprimido automaticamente)
with open("audio_grande.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcription/",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )
    result = response.json()
    print(f"Texto: {result['text']}")
    print(f"Foi comprimido: {result['compressed']}")

# 4. Transcrever áudio (via base64)
with open("audio.mp3", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/transcription/base64",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "audio_base64": audio_base64,
        "filename": "audio.mp3"
    }
)
print(response.json())
```

### JavaScript/Node.js

```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

// 1. Obter token
const tokenResponse = await axios.post('http://localhost:8000/auth/token', {
  user_id: 'user123'
});
const token = tokenResponse.data.access_token;

// 2. Transcrever áudio
const formData = new FormData();
formData.append('file', fs.createReadStream('audio.mp3'));

const response = await axios.post('http://localhost:8000/transcription/', formData, {
  headers: {
    'Authorization': `Bearer ${token}`,
    ...formData.getHeaders()
  }
});

console.log(response.data.text);
```

## Docker

Este projeto está totalmente containerizado com Docker! Veja instruções completas em [DOCKER.md](DOCKER.md).

### Quick Start com Docker

```bash
# 1. Configure o .env com suas credenciais
# 2. Execute:
docker-compose up -d --build

# 3. Acesse:
http://localhost:8000/docs
```

### Comandos úteis

```bash
# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Rebuild após mudanças
docker-compose up -d --build
```

## Desenvolvimento

Para contribuir com o projeto:

1. Clone o repositório
2. Crie uma branch para sua feature
3. Faça suas alterações
4. Teste localmente (com Docker ou ambiente virtual)
5. Envie um pull request

## Por que apenas WAV suporta compressão?

Para comprimir outros formatos (MP3, M4A, etc.) seria necessário:
- FFmpeg ou bibliotecas externas pesadas
- Decodificação + recodificação (lento e complexo)

Com WAV:
- ✅ Formato descomprimido nativo
- ✅ Bibliotecas Python puras (wave + audioop)
- ✅ Rápido e sem dependências externas

**Solução:** Se você tem arquivos MP3/M4A grandes, converta para WAV antes de enviar para aproveitar a compressão automática.

## Troubleshooting

### Arquivo muito grande

Se você receber erro "Arquivo muito grande" para formatos não-WAV:
- Converta o arquivo para WAV
- Ou use uma ferramenta externa para comprimir antes de enviar

### Erro de memória com áudios grandes

Para áudios muito grandes (> 50MB), mesmo WAV, pode haver problemas:
```bash
uvicorn app.main:app --limit-max-requests 1000 --timeout-keep-alive 300
```

## Licença

MIT
