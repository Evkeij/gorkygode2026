"""
Распознавание речи из WAV-файла через Google Speech Recognition.
Используется Electron-приложением.
"""

import json
import sys

import speech_recognition as sr


def main():
    # Принудительно используем UTF-8 для вывода русских символов.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"text": "", "error": "Не передан путь к аудиофайлу"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    audio_path = sys.argv[1]

    recognizer = sr.Recognizer()

    # Максимальное время ожидания ответа от сервиса — 15 секунд.
    recognizer.operation_timeout = 15

    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="ru-RU")

        print(json.dumps({"text": text.strip(), "error": None}, ensure_ascii=False))

    except sr.UnknownValueError:
        print(
            json.dumps(
                {"text": "", "error": "Не удалось распознать речь"}, ensure_ascii=False
            )
        )
        sys.exit(1)

    except sr.RequestError as error:
        print(
            json.dumps(
                {"text": "", "error": f"Ошибка сервиса распознавания: {error}"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    except Exception as error:
        print(json.dumps({"text": "", "error": str(error)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
