# Usar imagem Python slim (mais leve)
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar apenas requirements primeiro (cache de layers do Docker)
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Expor a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação com timeouts aumentados
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "30"]
