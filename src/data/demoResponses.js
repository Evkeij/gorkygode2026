
export function getDemoResponse(text) {
  const normalizedText = text.toLowerCase().trim();

  if (
    normalizedText.includes('привет') ||
    normalizedText.includes('здравствуй')
  ) {
    return 'Привет! Рад тебя видеть. Чем займёмся сегодня?';
  }

  if (
    normalizedText.includes('время') ||
    normalizedText.includes('день')
  ) {
    return 'Давай составим план и выделим самое важное на сегодня.';
  }

  if (
    normalizedText.includes('помоги') ||
    normalizedText.includes('помощь')
  ) {
    return 'Конечно! Расскажи подробнее, что нужно сделать.';
  }

  if (
    normalizedText.includes('идея') ||
    normalizedText.includes('проект')
  ) {
    return 'Давай разберём задачу и подумаем над несколькими вариантами решения.';
  }

  return 'Я получил твоё сообщение. Пока я работаю в демонстрационном режиме, поэтому мои ответы заранее подготовлены.';
}
