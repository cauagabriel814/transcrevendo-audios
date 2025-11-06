# Configuração do Nginx para Resolver Timeout

## Problema
O Nginx está cortando a conexão após 60 segundos, mesmo com o uvicorn configurado para 10 minutos.

## Solução: Ajustar o Nginx

### 1. Localizar o arquivo de configuração do Nginx

```bash
# Normalmente está em um destes locais:
/etc/nginx/sites-available/seu-site
/etc/nginx/conf.d/seu-site.conf
/etc/nginx/nginx.conf
```

### 2. Adicionar/modificar as seguintes diretivas no bloco `location`

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;

        # IMPORTANTE: Aumentar timeouts
        proxy_read_timeout 600s;           # 10 minutos
        proxy_connect_timeout 600s;        # 10 minutos
        proxy_send_timeout 600s;           # 10 minutos

        # Aumentar tamanho máximo do body (para upload de arquivos)
        client_max_body_size 100M;

        # Headers necessários
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Desabilitar buffering para streaming
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

### 3. Se usar no bloco `http` (global), adicione:

```nginx
http {
    # Timeouts globais
    client_body_timeout 600s;
    client_header_timeout 600s;
    send_timeout 600s;

    # Tamanho máximo do body
    client_max_body_size 100M;

    # ... resto da configuração
}
```

### 4. Testar e recarregar o Nginx

```bash
# Testar configuração
sudo nginx -t

# Se estiver OK, recarregar
sudo systemctl reload nginx

# Ou reiniciar
sudo systemctl restart nginx
```

## Exemplo Completo de Configuração

```nginx
server {
    listen 80;
    server_name api.exemplo.com;

    # Logs
    access_log /var/log/nginx/api_access.log;
    error_log /var/log/nginx/api_error.log;

    # Timeouts e limites
    client_max_body_size 100M;
    client_body_timeout 600s;
    client_header_timeout 600s;
    send_timeout 600s;

    location / {
        # Proxy para uvicorn
        proxy_pass http://127.0.0.1:8000;

        # Timeouts do proxy
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Buffering
        proxy_buffering off;
        proxy_request_buffering off;

        # Upgrade para WebSocket (se necessário no futuro)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Verificar se funcionou

Após aplicar as configurações:

```bash
# Ver logs em tempo real
sudo tail -f /var/log/nginx/api_error.log

# Fazer uma requisição de teste
curl -X POST "http://seu-dominio.com/transcription/" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@audio.mp3" \
  --max-time 700
```

## Outros componentes que podem causar timeout

### Apache (se for o caso)
```apache
<Location />
    ProxyPass http://localhost:8000/
    ProxyPassReverse http://localhost:8000/

    # Timeouts
    ProxyTimeout 600
</Location>

# No httpd.conf ou apache2.conf
Timeout 600
```

### Gunicorn (se estiver usando)
```bash
gunicorn app.main:app --timeout 600 --workers 4
```

### Systemd (se o serviço tiver TimeoutStartSec)
```ini
# /etc/systemd/system/seu-servico.service
[Service]
TimeoutStartSec=600
TimeoutStopSec=600
```
