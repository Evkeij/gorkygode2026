"""
Скрипт синтеза речи через Yandex SpeechKit.
Принимает текст, сохраняет mp3 и возвращает путь к файлу в JSON.
"""

import json
import os
import sys
import tempfile

import requests
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

YANDEX_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY") or os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER") or os.getenv("YANDEX_FOLDER")


def main():
    """Синтезирует речь из переданного текста и сохраняет результат во временный файл."""
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Не передан текст"}, ensure_ascii=False))
        sys.exit(1)

    if not YANDEX_API_KEY or not YANDEX_FOLDER:
        print(json.dumps({"ok": False, "error": "Не заданы ключи в .env"}, ensure_ascii=False))
        sys.exit(1)

    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print(json.dumps({"ok": False, "error": "Пустой текст"}, ensure_ascii=False))
        sys.exit(1)

    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}

    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": "alena",
        "emotion": "neutral",
        "format": "mp3",
        "folderId": YANDEX_FOLDER,
        "speed": "1.0",
    }

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=30)

        if resp.status_code != 200:
            print(json.dumps(
                {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"},
                ensure_ascii=False,
            ))
            sys.exit(1)

        # Сохраняем аудиофайл во временную папку Windows
        out_path = os.path.join(tempfile.gettempdir(), "reply.mp3")
        with open(out_path, "wb") as f:
            f.write(resp.content)

        print(json.dumps({"ok": True, "file": out_path, "error": None}, ensure_ascii=False))

    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
