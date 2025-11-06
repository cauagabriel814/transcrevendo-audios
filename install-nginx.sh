#!/bin/bash

# Script para instalar e configurar Nginx para Audio Transcription Service
# Execute com: bash install-nginx.sh

set -e  # Parar em caso de erro

echo "========================================="
echo "  Instalação Nginx - Audio Transcription"
echo "========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Este script precisa ser executado como root${NC}"
    echo "Execute: sudo bash install-nginx.sh"
    exit 1
fi

echo -e "${GREEN}✓ Verificação de permissões OK${NC}"
echo ""

# 1. Instalar Nginx (se não estiver instalado)
echo "1. Verificando instalação do Nginx..."
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nginx não encontrado. Instalando...${NC}"
    apt-get update
    apt-get install -y nginx
    echo -e "${GREEN}✓ Nginx instalado com sucesso${NC}"
else
    echo -e "${GREEN}✓ Nginx já está instalado${NC}"
fi
echo ""

# 2. Parar Nginx temporariamente
echo "2. Parando Nginx temporariamente..."
systemctl stop nginx
echo -e "${GREEN}✓ Nginx parado${NC}"
echo ""

# 3. Backup da configuração antiga (se existir)
echo "3. Fazendo backup de configurações antigas..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f /etc/nginx/sites-available/audio-transcription ]; then
    cp /etc/nginx/sites-available/audio-transcription /etc/nginx/sites-available/audio-transcription.backup.$TIMESTAMP
    echo -e "${GREEN}✓ Backup criado: audio-transcription.backup.$TIMESTAMP${NC}"
fi
echo ""

# 4. Copiar novo arquivo de configuração
echo "4. Copiando nova configuração..."
if [ ! -f nginx.conf ]; then
    echo -e "${RED}❌ Arquivo nginx.conf não encontrado no diretório atual${NC}"
    echo "Certifique-se de estar no diretório do projeto"
    exit 1
fi

cp nginx.conf /etc/nginx/sites-available/audio-transcription
echo -e "${GREEN}✓ Configuração copiada para /etc/nginx/sites-available/audio-transcription${NC}"
echo ""

# 5. Solicitar domínio (opcional)
echo "5. Configuração do domínio..."
echo -e "${YELLOW}Digite seu domínio (ex: api.seudominio.com) ou pressione ENTER para usar '_' (qualquer domínio):${NC}"
read -p "Domínio: " DOMAIN

if [ ! -z "$DOMAIN" ]; then
    sed -i "s/server_name _;/server_name $DOMAIN;/" /etc/nginx/sites-available/audio-transcription
    echo -e "${GREEN}✓ Domínio configurado: $DOMAIN${NC}"
else
    echo -e "${GREEN}✓ Usando configuração padrão (qualquer domínio)${NC}"
fi
echo ""

# 6. Criar link simbólico
echo "6. Ativando configuração..."
if [ -L /etc/nginx/sites-enabled/audio-transcription ]; then
    rm /etc/nginx/sites-enabled/audio-transcription
fi
ln -s /etc/nginx/sites-available/audio-transcription /etc/nginx/sites-enabled/audio-transcription
echo -e "${GREEN}✓ Configuração ativada${NC}"
echo ""

# 7. Remover configuração default (se existir)
echo "7. Removendo configuração default (se existir)..."
if [ -L /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
    echo -e "${GREEN}✓ Configuração default removida${NC}"
else
    echo -e "${YELLOW}⚠️  Configuração default não encontrada (tudo bem)${NC}"
fi
echo ""

# 8. Testar configuração
echo "8. Testando configuração do Nginx..."
if nginx -t; then
    echo -e "${GREEN}✓ Configuração válida!${NC}"
else
    echo -e "${RED}❌ Erro na configuração. Restaurando backup...${NC}"
    if [ -f /etc/nginx/sites-available/audio-transcription.backup.$TIMESTAMP ]; then
        cp /etc/nginx/sites-available/audio-transcription.backup.$TIMESTAMP /etc/nginx/sites-available/audio-transcription
    fi
    exit 1
fi
echo ""

# 9. Iniciar Nginx
echo "9. Iniciando Nginx..."
systemctl start nginx
systemctl enable nginx
echo -e "${GREEN}✓ Nginx iniciado e configurado para iniciar no boot${NC}"
echo ""

# 10. Verificar status
echo "10. Verificando status..."
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx está rodando!${NC}"
else
    echo -e "${RED}❌ Nginx não está rodando${NC}"
    exit 1
fi
echo ""

# 11. Informações finais
echo "========================================="
echo -e "${GREEN}  ✓ INSTALAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo "========================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1. Certifique-se que seu serviço FastAPI está rodando na porta 8000:"
echo "   $ docker-compose ps"
echo "   $ curl http://localhost:8000/health"
echo ""
echo "2. Teste o proxy do Nginx:"
if [ ! -z "$DOMAIN" ]; then
    echo "   $ curl http://$DOMAIN/health"
else
    echo "   $ curl http://seu-ip/health"
fi
echo ""
echo "3. Veja os logs em tempo real:"
echo "   $ tail -f /var/log/nginx/audio_transcription_access.log"
echo "   $ tail -f /var/log/nginx/audio_transcription_error.log"
echo ""
echo "4. Para testar transcrição completa:"
echo "   $ curl -X POST 'http://seu-dominio/auth/token' -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'"
echo ""
echo "Configurações aplicadas:"
echo "  - Timeouts: 600 segundos (10 minutos)"
echo "  - Max body size: 150MB"
echo "  - Keep-alive: 600 segundos"
echo "  - Buffering: desabilitado"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE: O timeout de 60s foi RESOLVIDO!${NC}"
echo ""
