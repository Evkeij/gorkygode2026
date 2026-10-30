"""
Обёртка для запуска FastAPI через uvicorn.
Используется при сборке backend.exe с помощью PyInstaller.
"""

import uvicorn

if __name__ == "__main__":
    # Запускаем сервер программно, чтобы PyInstaller это увидел
    uvicorn.run("Api:app", host="127.0.0.1", port=8000, log_level="info")
