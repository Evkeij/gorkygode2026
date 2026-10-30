# -*- coding: utf-8 -*-
import sys
import json
import speech_recognition as sr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"text": "", "error": "Не передан путь к аудиофайлу"},
                ensure_ascii=True,
            )
        )
        sys.exit(1)

    audio_path = sys.argv[1]
    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="ru-RU")
        print(json.dumps({"text": text.strip(), "error": None}, ensure_ascii=True))

    except sr.UnknownValueError:
        print(
            json.dumps(
                {"text": "", "error": "Не удалось распознать речь"}, ensure_ascii=True
            )
        )
        sys.exit(1)

    except sr.RequestError as error:
        print(
            json.dumps(
                {"text": "", "error": f"Ошибка сервиса распознавания: {error}"},
                ensure_ascii=True,
            )
        )
        sys.exit(1)

    except Exception as error:
        print(json.dumps({"text": "", "error": str(error)}, ensure_ascii=True))
        sys.exit(1)

if __name__ == "__main__":
    main()
