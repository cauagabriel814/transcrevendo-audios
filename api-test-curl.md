# API Test - cURL Commands

Este documento contém exemplos de comandos cURL para testar todas as rotas da API de transcrição de áudio.

**Base URL:** `http://localhost:8000`

---

## 📋 Índice

1. [Autenticação](#autenticação)
2. [Rotas Públicas](#rotas-públicas)
3. [Rotas de Transcrição](#rotas-de-transcrição)
4. [Workflow Completo](#workflow-completo)

---

## 🔐 Autenticação

### Gerar Token JWT

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

**Resposta esperada:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_hours": 3
}
```

### Salvar Token em Variável (Linux/Mac)

```bash
# Obter token e salvar em arquivo
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }' \
  -o token.json

# Extrair token para variável (requer jq)
TOKEN=$(cat token.json | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Salvar Token em Variável (Windows PowerShell)

```powershell
# Obter token
$response = Invoke-RestMethod -Uri "http://localhost:8000/auth/token" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"your_password"}'

# Extrair token
$TOKEN = $response.access_token
Write-Host "Token: $TOKEN"
```

---

## 🌐 Rotas Públicas

### 1. Root - Informações da API

```bash
curl -X GET "http://localhost:8000/"
```

**Resposta:**
```json
{
  "service": "Audio Transcription Service",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/transcription/health"
}
```

---

### 2. Health Check Geral

```bash
curl -X GET "http://localhost:8000/health"
```

**Resposta:**
```json
{
  "status": "healthy",
  "service": "Audio Transcription Service"
}
```

---

### 3. Health Check do Serviço de Transcrição

```bash
curl -X GET "http://localhost:8000/transcription/health"
```

**Resposta:**
```json
{
  "status": "healthy",
  "service": "transcription"
}
```

---

## 🎤 Rotas de Transcrição

> **⚠️ Importante:** Todas as rotas de transcrição requerem autenticação via Bearer Token.

### 1. Transcrever Arquivo de Áudio (Upload)

**Formatos suportados:** mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
**Tamanho máximo:** 25MB (arquivos WAV maiores são automaticamente comprimidos)

```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -F "file=@/caminho/para/audio.mp3"
```

**Exemplo com variável de token (Linux/Mac):**
```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3"
```

**Exemplo com variável de token (Windows PowerShell):**
```powershell
$headers = @{
  "Authorization" = "Bearer $TOKEN"
}

$form = @{
  file = Get-Item -Path "audio.mp3"
}

Invoke-RestMethod -Uri "http://localhost:8000/transcription/" `
  -Method POST `
  -Headers $headers `
  -Form $form
```

**Resposta esperada:**
```json
{
  "text": "Este é o texto transcrito do áudio",
  "language": "pt",
  "duration": 2.5,
  "compressed": false
}
```

---

### 2. Transcrever Arquivo WAV Grande (com compressão automática)

```bash
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio_grande.wav"
```

**Resposta esperada (arquivo comprimido):**
```json
{
  "text": "Este é o texto transcrito do áudio",
  "language": "pt",
  "duration": 3.2,
  "compressed": true
}
```

> **📝 Nota:** Arquivos WAV maiores que 25MB são automaticamente convertidos para mono e reduzidos para 16kHz antes da transcrição.

---

### 3. Transcrever Áudio via Base64

**Formatos suportados:** mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac

#### Passo 1: Converter áudio para Base64

**Linux/Mac:**
```bash
AUDIO_BASE64=$(base64 -w 0 audio.mp3)
```

**Windows PowerShell:**
```powershell
$AUDIO_BASE64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("audio.mp3"))
```

#### Passo 2: Enviar requisição

**Linux/Mac:**
```bash
curl -X POST "http://localhost:8000/transcription/base64" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_base64\": \"$AUDIO_BASE64\",
    \"filename\": \"audio.mp3\"
  }"
```

**Windows PowerShell:**
```powershell
$headers = @{
  "Authorization" = "Bearer $TOKEN"
  "Content-Type" = "application/json"
}

$body = @{
  audio_base64 = $AUDIO_BASE64
  filename = "audio.mp3"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/transcription/base64" `
  -Method POST `
  -Headers $headers `
  -Body $body
```

**Exemplo completo (arquivo pequeno):**
```bash
curl -X POST "http://localhost:8000/transcription/base64" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "SGVsbG8gV29ybGQh...",
    "filename": "audio.mp3"
  }'
```

**Resposta esperada:**
```json
{
  "text": "Este é o texto transcrito do áudio",
  "language": "pt",
  "duration": 2.5,
  "compressed": false
}
```

---

## 🔄 Workflow Completo

### Exemplo 1: Autenticar e Transcrever Arquivo

```bash
# 1. Obter token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# 2. Verificar se token foi obtido
echo "Token obtido: $TOKEN"

# 3. Transcrever áudio
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3" \
  -o transcription.json

# 4. Ver resultado
cat transcription.json
```

---

### Exemplo 2: Workflow Completo com Base64

```bash
# 1. Obter token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# 2. Converter áudio para Base64
AUDIO_BASE64=$(base64 -w 0 audio.mp3)

# 3. Transcrever
curl -X POST "http://localhost:8000/transcription/base64" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_base64\": \"$AUDIO_BASE64\",
    \"filename\": \"audio.mp3\"
  }" \
  | jq '.'
```

---

### Exemplo 3: Testar Múltiplos Arquivos

```bash
# Obter token uma vez
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# Transcrever múltiplos arquivos
for file in *.mp3; do
  echo "Transcrevendo: $file"
  curl -X POST "http://localhost:8000/transcription/" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$file" \
    -o "${file%.mp3}_transcription.json"
  echo "Salvo em: ${file%.mp3}_transcription.json"
done
```

---

## 📊 Códigos de Status HTTP

| Código | Significado | Descrição |
|--------|-------------|-----------|
| 200 | Success | Requisição bem-sucedida |
| 400 | Bad Request | Formato de arquivo inválido ou Base64 inválido |
| 401 | Unauthorized | Token inválido, expirado ou credenciais incorretas |
| 413 | Payload Too Large | Arquivo excede o limite de tamanho |
| 500 | Internal Server Error | Erro no processamento |

---

## 🛠️ Variáveis de Ambiente Necessárias

Para que a API funcione corretamente, configure o arquivo `.env`:

```env
OPENAI_API_KEY=sk-your-openai-key-here
SECRET_KEY=your-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=3
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

---

## 📚 Documentação Adicional

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 💡 Dicas

1. **Token expira em 3 horas** - Gere um novo token se receber erro 401
2. **Formatos recomendados:** MP3 ou M4A para melhor relação qualidade/tamanho
3. **WAV grandes:** São automaticamente comprimidos (mono 16kHz) antes da transcrição
4. **Base64:** Útil para integração com sistemas que não suportam multipart/form-data
5. **Logs:** Verifique a pasta `/logs` para debug de requisições

---

## 🔍 Troubleshooting

### Erro 401 - Unauthorized
```bash
# Verifique se o token está válido
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3" \
  -v  # verbose mode para ver detalhes do erro
```

### Erro 413 - File Too Large
```bash
# Verifique o tamanho do arquivo
ls -lh audio.mp3

# Para WAV: deve ser <50MB (será comprimido automaticamente)
# Para outros formatos: deve ser <25MB
```

### Erro 400 - Invalid Format
```bash
# Verifique a extensão do arquivo
file audio.mp3

# Formatos válidos: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
```
