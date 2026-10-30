"""Получение эмбеддингов через Yandex Cloud (OpenAI-совместимый API)."""
EMBEDDING_DOC_MODEL = "text-embeddings-v2-query/latest"
EMBEDDING_QUERY_MODEL = "text-embeddings-v2-query/latest"

RECORD_TYPE_LABELS = {
    "meeting": "Встреча",
    "reminder": "Напоминание",
    "task": "Задача",
}


def build_embedding_text(record_type, title):
    """Текст записи, по которому считается эмбеддинг."""
    label = RECORD_TYPE_LABELS.get(record_type, "Запись")
    return f"{label}: {title}"


class Embedder:
    """Тонкая обёртка над embeddings API. При ошибке возвращает None."""

    def __init__(
        self,
        client,
        folder,
        doc_model=EMBEDDING_DOC_MODEL,
        query_model=EMBEDDING_QUERY_MODEL,
    ):
        self.client = client
        self.folder = folder
        self.doc_model = doc_model
        self.query_model = query_model

    def _embed(self, text, model):
        text = (text or "").strip()

        if not text:
            return None

        try:
            response = self.client.embeddings.create(
                model=f"emb://{self.folder}/{model}",
                input=text,
                # Явно просим float: SDK по умолчанию может запросить
                # base64, а не все совместимые API это поддерживают.
                encoding_format="float",
            )
            return list(response.data[0].embedding)
        except Exception as error:
            print(f"Ошибка эмбеддинга: {error}")
            return None

    def embed_document(self, text):
        """Эмбеддинг записи (сохраняется вместе с записью)."""
        return self._embed(text, self.doc_model)

    def embed_query(self, text):
        """Эмбеддинг поискового запроса."""
        return self._embed(text, self.query_model)
