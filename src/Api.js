const BASE = 'http://127.0.0.1:8000';

export async function sendChat(text) {
  try {
    const res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error(`Ошибка сервера (${res.status}):`, errorText);
      throw new Error(`Сервер ответил ошибкой: ${res.status}`);
    }

    const data = await res.json();
    if (!data || data.error) {
      console.error('Ошибка в ответе сервера:', data);
      throw new Error(data?.error || 'Пустой ответ от сервера');
    }
    return data;

  } catch (error) {
    console.error('Ошибка сети при запросе к бэкенду:', error);
    throw error; 
  }
}