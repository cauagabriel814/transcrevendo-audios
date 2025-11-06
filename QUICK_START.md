# Quick Start - Audio Transcription Service

Guia rápido para começar a usar o microserviço em 5 minutos! ⚡

## 🚀 Opção 1: Docker (Mais Rápido)

### Passo 1: Configure as credenciais

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o .env e adicione:
# - OPENAI_API_KEY (obtenha em: https://platform.openai.com/api-keys)
# - SECRET_KEY (gere com: openssl rand -hex 32)
```

### Passo 2: Execute

```bash
docker-compose up -d --build
```

### Passo 3: Teste

Acesse: http://localhost:8000/docs

Pronto! 🎉

---

## 🐍 Opção 2: Python Local

### Passo 1: Crie ambiente virtual

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Passo 2: Instale dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Configure credenciais

```bash
# Edite o arquivo .env
# Adicione OPENAI_API_KEY e SECRET_KEY
```

### Passo 4: Execute

```bash
python run.py
```

### Passo 5: Teste

Acesse: http://localhost:8000/docs

---

## 📝 Testando a API

### 1. Obter Token JWT

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_hours": 3
}
```

**Copie o `access_token` para usar nas próximas requisições!**

### 2. Transcrever um áudio

```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -F "file=@/caminho/do/seu/audio.mp3"
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

---

## 🎯 Casos de Uso Comuns

### Transcrever áudio pequeno (< 25MB)

```python
import requests

# 1. Obter token
response = requests.post(
    "http://localhost:8000/auth/token",
    json={"user_id": "user123"}
)
token = response.json()["access_token"]

# 2. Transcrever
with open("audio.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcription/",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )

print(response.json()["text"])
```

### Transcrever áudio grande (WAV > 25MB)

```python
# Mesmo código acima, mas use arquivo .wav
# O sistema comprime automaticamente!

with open("audio_grande.wav", "rb") as f:  # Até 50MB
    response = requests.post(
        "http://localhost:8000/transcription/",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )

result = response.json()
print(f"Texto: {result['text']}")
print(f"Foi comprimido? {result['compressed']}")
```

### Transcrever via Base64

```python
import base64

# Converter áudio para base64
with open("audio.mp3", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

# Transcrever
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

---

## 🔧 Comandos Úteis

### Docker

```bash
# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Rebuild após mudanças
docker-compose up -d --build
```

### Makefile (se disponível)

```bash
make help          # Ver todos comandos
make docker-up     # Iniciar com Docker
make docker-logs   # Ver logs
make docker-down   # Parar
```

---

## ❓ Problemas Comuns

### Erro: "Token inválido"

- Verifique se copiou o token completo
- O token expira em 3 horas, gere um novo

### Erro: "Arquivo muito grande"

- Para MP3/M4A: máximo 25MB
- Para WAV: máximo ~50MB (com compressão automática)
- Solução: Converta para WAV se for maior que 25MB

### Erro: "OpenAI API key inválida"

- Verifique se a chave no `.env` está correta
- Teste a chave em: https://platform.openai.com/api-keys

### Porta 8000 já em uso

```bash
# Windows
netstat -ano | findstr :8000
# Mate o processo ou use outra porta

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

---

## 📚 Próximos Passos

- ✅ Leia a [documentação completa](README.md)
- ✅ Veja [exemplos avançados](examples.http)
- ✅ Aprenda mais sobre [Docker](DOCKER.md)
- ✅ Acesse a documentação interativa em `/docs`

---

## 🆘 Precisa de Ajuda?

- 📖 [README.md](README.md) - Documentação completa
- 🐳 [DOCKER.md](DOCKER.md) - Guia Docker detalhado
- 🔍 `/docs` - Documentação interativa da API
- 🌐 [Issues](https://github.com/your-repo/issues) - Reporte problemas

Boa transcrição! 🎙️✨
