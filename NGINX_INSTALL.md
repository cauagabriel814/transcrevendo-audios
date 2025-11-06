# Instalação e Configuração do Nginx

Este guia ensina como instalar e configurar o Nginx para resolver o problema de timeout de 60 segundos.

## 🚀 Instalação Automática (Recomendado)

```bash
# 1. Na VPS, vá para o diretório do projeto
cd /caminho/para/residire-treatment-audio

# 2. Dê permissão de execução
chmod +x install-nginx.sh

# 3. Execute o script (como root)
sudo bash install-nginx.sh
```

O script irá:
- ✅ Instalar o Nginx (se necessário)
- ✅ Fazer backup das configurações antigas
- ✅ Copiar e ativar a nova configuração
- ✅ Configurar todos os timeouts para 10 minutos
- ✅ Testar e iniciar o Nginx
- ✅ Ativar no boot

## 📝 Instalação Manual

Se preferir instalar manualmente:

### 1. Instalar Nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### 2. Copiar configuração

```bash
# Copiar o arquivo nginx.conf do projeto
sudo cp nginx.conf /etc/nginx/sites-available/audio-transcription

# Editar e substituir 'server_name _;' pelo seu domínio
sudo nano /etc/nginx/sites-available/audio-transcription
# Altere: server_name _;
# Para: server_name api.seudominio.com;
```

### 3. Ativar configuração

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/audio-transcription /etc/nginx/sites-enabled/

# Remover configuração default
sudo rm /etc/nginx/sites-enabled/default
```

### 4. Testar e reiniciar

```bash
# Testar configuração
sudo nginx -t

# Se estiver OK, reiniciar
sudo systemctl restart nginx

# Verificar status
sudo systemctl status nginx
```

## ✅ Verificação

### 1. Verificar se Nginx está rodando

```bash
sudo systemctl status nginx
```

Deve mostrar: **active (running)**

### 2. Testar health check

```bash
# Testar localmente
curl http://localhost/health

# Testar pelo domínio
curl http://seu-dominio.com/health
```

Deve retornar:
```json
{
  "status": "healthy",
  "service": "Audio Transcription Service"
}
```

### 3. Verificar timeouts configurados

```bash
# Ver configurações de timeout
sudo grep -r "timeout" /etc/nginx/sites-available/audio-transcription
```

Deve mostrar:
```nginx
client_body_timeout 600s;
client_header_timeout 600s;
send_timeout 600s;
keepalive_timeout 600s;
proxy_read_timeout 600s;
proxy_connect_timeout 600s;
proxy_send_timeout 600s;
```

### 4. Testar transcrição completa

```bash
# 1. Gerar token
TOKEN=$(curl -s -X POST 'http://seu-dominio/auth/token' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# 2. Testar transcrição
curl -X POST "http://seu-dominio/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3" \
  --max-time 700 \
  -w "\nTempo total: %{time_total}s\n"
```

## 📊 Logs

### Ver logs em tempo real

```bash
# Logs de acesso
sudo tail -f /var/log/nginx/audio_transcription_access.log

# Logs de erro
sudo tail -f /var/log/nginx/audio_transcription_error.log
```

### Ver logs do serviço FastAPI

```bash
# Se estiver usando Docker
docker-compose logs -f

# Se estiver usando systemd
sudo journalctl -u seu-servico -f
```

## 🔧 Troubleshooting

### Problema: Nginx não inicia

```bash
# Ver erro específico
sudo nginx -t

# Ver logs de erro
sudo tail -50 /var/log/nginx/error.log
```

### Problema: Porta 8000 não está acessível

```bash
# Verificar se o serviço está rodando
curl http://localhost:8000/health

# Verificar portas abertas
sudo netstat -tlnp | grep :8000
```

### Problema: Ainda acontece timeout

```bash
# 1. Verificar se as configurações foram aplicadas
sudo nginx -t
sudo systemctl restart nginx  # RESTART, não reload!

# 2. Verificar se o backend está com timeout configurado
# Veja os logs do FastAPI
docker-compose logs | grep -i timeout

# 3. Testar direto no backend (sem Nginx)
sudo systemctl stop nginx
curl -X POST "http://localhost:8000/transcription/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3"
```

Se funcionar SEM Nginx, o problema está na configuração do Nginx.

### Problema: CloudFlare ou CDN está causando timeout

Se você usa CloudFlare:

1. Vá no painel do CloudFlare
2. Clique no domínio
3. Clique no ícone da nuvem laranja para desativar o proxy (fica cinza)
4. Ou configure o timeout no CloudFlare Workers

## 🔐 Configurar HTTPS (Opcional)

Para produção, é recomendado usar HTTPS:

```bash
# 1. Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# 2. Obter certificado SSL
sudo certbot --nginx -d api.seudominio.com

# 3. O certbot vai modificar automaticamente o nginx.conf
# 4. Testar renovação automática
sudo certbot renew --dry-run
```

Depois, descomente a seção HTTPS no arquivo `nginx.conf`.

## 📋 Checklist Final

Antes de considerar concluído:

- [ ] Nginx instalado e rodando
- [ ] Configuração copiada para `/etc/nginx/sites-available/`
- [ ] Link simbólico criado em `/etc/nginx/sites-enabled/`
- [ ] `nginx -t` passou sem erros
- [ ] Nginx reiniciado com `systemctl restart nginx`
- [ ] Health check funcionando: `curl http://dominio/health`
- [ ] Transcrição completa funciona sem timeout de 60s
- [ ] Logs sendo gravados em `/var/log/nginx/`

## 🎯 Configurações Importantes

O arquivo `nginx.conf` já vem com:

| Configuração | Valor | Descrição |
|-------------|-------|-----------|
| `client_body_timeout` | 600s | Tempo para cliente enviar body |
| `client_header_timeout` | 600s | Tempo para cliente enviar headers |
| `send_timeout` | 600s | Tempo para enviar resposta |
| `keepalive_timeout` | 600s | Manter conexão aberta |
| `proxy_read_timeout` | 600s | Tempo para ler do backend |
| `proxy_connect_timeout` | 600s | Tempo para conectar ao backend |
| `proxy_send_timeout` | 600s | Tempo para enviar ao backend |
| `client_max_body_size` | 150M | Tamanho máximo do body |
| `proxy_buffering` | off | Desabilitar buffering |

**Todas as configurações são para 10 minutos (600 segundos)**, resolvendo o timeout de 60s!

## 📞 Suporte

Se ainda tiver problemas após seguir este guia:

1. Execute o script de diagnóstico:
   ```bash
   bash diagnose_timeout.sh
   ```

2. Veja os arquivos de troubleshooting:
   - `TROUBLESHOOTING_TIMEOUT.md`
   - `nginx-config.md`

3. Verifique os logs do Nginx e FastAPI em tempo real
