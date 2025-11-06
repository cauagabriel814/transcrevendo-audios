#!/bin/bash

echo "========================================="
echo "  Diagnóstico de Timeout - VPS"
echo "========================================="
echo ""

echo "1. Verificando processos Nginx:"
echo "-----------------------------------"
ps aux | grep nginx | grep -v grep
echo ""

echo "2. Verificando processos Gunicorn:"
echo "-----------------------------------"
GUNICORN_PROCESSES=$(ps aux | grep gunicorn | grep -v grep)
if [ -z "$GUNICORN_PROCESSES" ]; then
    echo "Gunicorn NÃO está rodando"
else
    echo "$GUNICORN_PROCESSES"
    echo ""
    echo "⚠️  ATENÇÃO: Gunicorn detectado!"
    echo "⚠️  O Gunicorn tem timeout padrão de 30s (ou configurado)"
    echo "⚠️  Você precisa aumentar o timeout do Gunicorn!"
fi
echo ""

echo "3. Verificando processos Python/Uvicorn:"
echo "-----------------------------------"
ps aux | grep "python.*run.py\|uvicorn" | grep -v grep
echo ""

echo "4. Verificando portas abertas:"
echo "-----------------------------------"
sudo netstat -tlnp | grep :8000
echo ""

echo "5. Última modificação dos arquivos Nginx:"
echo "-----------------------------------"
ls -lh /etc/nginx/sites-available/ 2>/dev/null || echo "Diretório não encontrado"
ls -lh /etc/nginx/conf.d/ 2>/dev/null || echo "Diretório não encontrado"
echo ""

echo "6. Procurando configurações de timeout no Nginx:"
echo "-----------------------------------"
sudo grep -r "timeout" /etc/nginx/sites-available/ 2>/dev/null | head -20
sudo grep -r "timeout" /etc/nginx/conf.d/ 2>/dev/null | head -20
echo ""

echo "7. Status do Nginx:"
echo "-----------------------------------"
sudo systemctl status nginx --no-pager | head -20
echo ""

echo "8. Verificando se há CloudFlare/Proxy:"
echo "-----------------------------------"
echo "Verificando DNS do domínio (se aplicável)..."
# Se tiver domínio, substituir abaixo
# dig seu-dominio.com
echo ""

echo "9. Teste de conexão direta ao uvicorn (localhost):"
echo "-----------------------------------"
curl -s -o /dev/null -w "Status: %{http_code} | Time: %{time_total}s\n" http://localhost:8000/health 2>&1
echo ""

echo "10. Verificando serviço systemd (se houver):"
echo "-----------------------------------"
ls /etc/systemd/system/ | grep -i "transcri\|audio\|api\|app" 2>/dev/null
echo ""

echo "========================================="
echo "  DIAGNÓSTICO COMPLETO"
echo "========================================="
echo ""
echo "Próximos passos:"
echo ""
echo "A. Se GUNICORN foi detectado (item 2):"
echo "   → Você DEVE adicionar --timeout 600 ao comando do Gunicorn"
echo "   → Ou configurar no arquivo de serviço systemd"
echo ""
echo "B. Se NÃO encontrou timeouts no Nginx (item 6):"
echo "   → A configuração do Nginx NÃO foi aplicada corretamente"
echo "   → Execute: sudo systemctl restart nginx (não reload!)"
echo ""
echo "C. Para testar SEM Nginx:"
echo "   sudo systemctl stop nginx"
echo "   # Teste direto na porta 8000"
echo "   # Se funcionar, o problema é no Nginx"
echo ""
