# Troubleshooting: Timeout de 60 segundos persistente

## Problema
Mesmo após ajustar o Nginx, o timeout de 60s continua ocorrendo.

## Checklist de Diagnóstico

### 1. Verificar se o Nginx foi REALMENTE recarregado

```bash
# Ver data da última modificação do arquivo
ls -l /etc/nginx/sites-available/seu-site

# Verificar se a configuração está correta
sudo nginx -t

# Recarregar Nginx (NÃO é reload, é restart)
sudo systemctl restart nginx

# Verificar se o processo foi reiniciado
sudo systemctl status nginx
ps aux | grep nginx
```

### 2. Verificar se está usando Gunicorn

```bash
# Verificar se há Gunicorn rodando
ps aux | grep gunicorn

# Se houver, o timeout dele também precisa ser aumentado
# Editar o arquivo de serviço ou comando de inicialização
```

**Se usar Gunicorn, ajuste assim:**

```bash
# No arquivo de serviço ou script de start
gunicorn app.main:app \
    --workers 4 \
    --timeout 600 \
    --keep-alive 600 \
    --bind 0.0.0.0:8000
```

**Ou no systemd service:**

```ini
# /etc/systemd/system/seu-servico.service
[Service]
ExecStart=/usr/local/bin/gunicorn app.main:app \
    --workers 4 \
    --timeout 600 \
    --keep-alive 600 \
    --bind 0.0.0.0:8000
```

### 3. Verificar se há LoadBalancer ou CloudFlare

```bash
# Ver headers da requisição
curl -I http://seu-dominio.com/health
```

Se houver **CloudFlare**:
- Vá no painel do CloudFlare
- Desative o proxy (ícone de nuvem laranja → cinza)
- Ou configure o timeout no CloudFlare Workers

Se houver **LoadBalancer** (AWS, GCP, etc):
- Ajuste o timeout no painel do serviço

### 4. Adicionar timeout no próprio FastAPI

Crie um arquivo `gunicorn.conf.py`:

```python
# gunicorn.conf.py
timeout = 600
keepalive = 600
worker_class = 'uvicorn.workers.UvicornWorker'
workers = 4
bind = '0.0.0.0:8000'
```

### 5. Verificar logs detalhados

```bash
# Log do Nginx em tempo real
sudo tail -f /var/log/nginx/error.log

# Log do seu serviço
sudo journalctl -u seu-servico -f

# Log do Python
tail -f logs/api_*.log
```

### 6. Testar diretamente no uvicorn (sem Nginx)

```bash
# Parar o Nginx temporariamente
sudo systemctl stop nginx

# Rodar o uvicorn diretamente
python run.py

# Em outro terminal, fazer o teste
curl -X POST "http://IP_DA_VPS:8000/transcription/" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@audio.mp3" \
  --max-time 700
```

Se funcionar SEM Nginx, o problema está no Nginx.

### 7. Configuração completa do Nginx (copiar e colar)

```nginx
# /etc/nginx/sites-available/seu-site

upstream transcription_backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name seu-dominio.com;

    # Logs
    access_log /var/log/nginx/transcription_access.log;
    error_log /var/log/nginx/transcription_error.log;

    # Timeouts globais do servidor
    client_body_timeout 600s;
    client_header_timeout 600s;
    send_timeout 600s;
    keepalive_timeout 600s;

    # Tamanho máximo do body
    client_max_body_size 150M;
    client_body_buffer_size 150M;

    location / {
        # Proxy
        proxy_pass http://transcription_backend;

        # Timeouts do proxy
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # HTTP/1.1 com keep-alive
        proxy_http_version 1.1;

        # Buffering
        proxy_buffering off;
        proxy_request_buffering off;

        # Upgrade para WebSocket
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Aplicar:**

```bash
# Copiar a configuração acima
sudo nano /etc/nginx/sites-available/seu-site

# Testar
sudo nginx -t

# Reiniciar (não reload!)
sudo systemctl restart nginx

# Verificar
sudo systemctl status nginx
```

### 8. Se estiver usando Docker

No `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TIMEOUT=600
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --timeout-keep-alive 600
```

### 9. Verificar configuração do systemd

```bash
# Editar o serviço
sudo nano /etc/systemd/system/seu-servico.service
```

Adicionar:

```ini
[Service]
Type=notify
NotifyAccess=all
TimeoutStartSec=600
TimeoutStopSec=600
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl restart seu-servico
```

### 10. Comando de diagnóstico completo

Execute este script na VPS:

```bash
#!/bin/bash

echo "=== Diagnóstico de Timeout ==="
echo ""

echo "1. Verificando Nginx:"
ps aux | grep nginx | grep -v grep
echo ""

echo "2. Verificando Gunicorn:"
ps aux | grep gunicorn | grep -v grep
echo ""

echo "3. Verificando Python:"
ps aux | grep "python.*run.py" | grep -v grep
echo ""

echo "4. Verificando portas:"
sudo netstat -tlnp | grep :8000
echo ""

echo "5. Última modificação do Nginx:"
ls -l /etc/nginx/sites-available/ | tail -5
echo ""

echo "6. Configuração do Nginx (timeouts):"
sudo grep -r "timeout" /etc/nginx/sites-available/ 2>/dev/null
echo ""

echo "7. Status do serviço:"
sudo systemctl status nginx --no-pager
echo ""

echo "8. Teste de conexão direta:"
curl -s -o /dev/null -w "Time: %{time_total}s\n" http://localhost:8000/health
```

## Solução Definitiva

Se NADA disso funcionar, o problema pode ser:

1. **CloudFlare ou CDN**: Desative temporariamente
2. **Firewall**: Verifique regras de timeout
3. **ISP/Provedor**: Alguns provedores têm timeout de 60s em conexões HTTP

### Teste final: Acessar direto pelo IP

```bash
# Na VPS, descubra o IP
hostname -I

# No cliente, teste direto pelo IP (sem domínio)
curl -X POST "http://IP_DA_VPS:8000/transcription/" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@audio.mp3"
```

Se funcionar pelo IP mas não pelo domínio, o problema está no DNS/CDN/CloudFlare.
