import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload em desenvolvimento
        timeout_keep_alive=120,  # Timeout de 2 minutos para conexões keep-alive
        limit_concurrency=100,  # Limite de conexões simultâneas
        limit_max_requests=10000,  # Máximo de requisições antes de reiniciar worker
        h11_max_incomplete_event_size=200 * 1024 * 1024,  # 200MB para requests grandes (base64)
    )
