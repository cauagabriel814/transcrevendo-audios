# Guia Docker - Audio Transcription Service

Este guia contém instruções detalhadas para rodar o serviço usando Docker.

## Pré-requisitos

- Docker instalado ([Download Docker](https://www.docker.com/products/docker-desktop))
- Docker Compose instalado (geralmente vem com Docker Desktop)

## Configuração

### 1. Configurar variáveis de ambiente

Edite o arquivo `.env` e adicione suas credenciais:

```env
OPENAI_API_KEY=sk-your-openai-key-here
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=3
```

**Gerar SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Comandos Docker Compose

### Build e executar

```bash
# Build e iniciar (modo interativo - vê os logs)
docker-compose up --build

# Build e iniciar em background
docker-compose up -d --build

# Apenas iniciar (sem rebuild)
docker-compose up -d
```

### Gerenciar containers

```bash
# Ver status dos containers
docker-compose ps

# Parar os containers
docker-compose stop

# Parar e remover containers
docker-compose down

# Parar, remover containers e volumes
docker-compose down -v
```

### Logs

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver últimas 100 linhas dos logs
docker-compose logs --tail=100

# Logs de um serviço específico
docker-compose logs -f api
```

### Reconstruir após mudanças no código

```bash
# Reconstruir e reiniciar
docker-compose up -d --build

# Forçar reconstrução sem cache
docker-compose build --no-cache
docker-compose up -d
```

## Comandos Docker (sem Compose)

### Build

```bash
# Build da imagem
docker build -t audio-transcription-api .

# Build sem cache
docker build --no-cache -t audio-transcription-api .
```

### Executar

```bash
# Executar em background
docker run -d \
  --name audio-transcription-api \
  -p 8000:8000 \
  --env-file .env \
  audio-transcription-api

# Executar com variáveis de ambiente diretas
docker run -d \
  --name audio-transcription-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-xxx \
  -e SECRET_KEY=your-secret \
  audio-transcription-api
```

### Gerenciar containers

```bash
# Listar containers rodando
docker ps

# Listar todos os containers
docker ps -a

# Parar container
docker stop audio-transcription-api

# Remover container
docker rm audio-transcription-api

# Parar e remover
docker rm -f audio-transcription-api
```

### Logs

```bash
# Ver logs
docker logs audio-transcription-api

# Ver logs em tempo real
docker logs -f audio-transcription-api

# Últimas 100 linhas
docker logs --tail=100 audio-transcription-api
```

### Acessar o container

```bash
# Executar bash dentro do container
docker exec -it audio-transcription-api bash

# Executar comando pontual
docker exec audio-transcription-api ls -la
```

## Health Check

O container tem health check configurado. Verificar status:

```bash
# Com docker-compose
docker-compose ps

# Com docker
docker ps
# Veja a coluna STATUS: "healthy" ou "unhealthy"

# Inspecionar detalhes do health check
docker inspect --format='{{json .State.Health}}' audio-transcription-api | python -m json.tool
```

## Troubleshooting

### Container não inicia

```bash
# Ver logs de erro
docker-compose logs

# Verificar se as portas estão em uso
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac
```

### Variáveis de ambiente não carregam

```bash
# Verificar se o .env existe
ls -la .env

# Ver variáveis dentro do container
docker exec audio-transcription-api env
```

### Rebuild não aplica mudanças

```bash
# Rebuild forçado sem cache
docker-compose build --no-cache
docker-compose up -d
```

### Limpar tudo e começar do zero

```bash
# Parar tudo
docker-compose down

# Remover imagem
docker rmi audio-transcription-api

# Rebuild e iniciar
docker-compose up --build
```

## Produção

### Usando Docker Hub

```bash
# Tag da imagem
docker tag audio-transcription-api username/audio-transcription-api:latest

# Push para Docker Hub
docker push username/audio-transcription-api:latest

# Pull em outro servidor
docker pull username/audio-transcription-api:latest
docker run -d -p 8000:8000 --env-file .env username/audio-transcription-api:latest
```

### Usando registro privado

```bash
# Tag para registro privado
docker tag audio-transcription-api registry.example.com/audio-transcription-api:latest

# Push
docker push registry.example.com/audio-transcription-api:latest
```

### Docker Compose em produção

Crie um `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: username/audio-transcription-api:latest
    container_name: audio-transcription-api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Execute:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Recursos

- [Documentação Docker](https://docs.docker.com/)
- [Documentação Docker Compose](https://docs.docker.com/compose/)
- [FastAPI com Docker](https://fastapi.tiangolo.com/deployment/docker/)
