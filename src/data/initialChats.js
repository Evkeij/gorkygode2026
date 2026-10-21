
export const initialChats = [
  {
    id: 1,
    title: 'Знакомство с DescVoice',
    messages: [
      {
        id: 1,
        role: 'assistant',
        content:
          'Привет! Я DescVoice — твой голосовой ассистент. Чем могу помочь?',
      },
    ],
  },
  {
    id: 2,
    title: 'Планирование дня',
    messages: [
      {
        id: 1,
        role: 'user',
        content: 'Помоги спланировать мой день.',
      },
      {
        id: 2,
        role: 'assistant',
        content:
          'Конечно! Давай определим главные задачи и распределим их по времени.',
      },
    ],
  },
  {
    id: 3,
    title: 'Идеи для проекта',
    messages: [
      {
        id: 1,
        role: 'user',
        content: 'Предложи идеи для нового проекта.',
      },
      {
        id: 2,
        role: 'assistant',
        content:
          'Можем начать с проблемы, которую ты хочешь решить, и подобрать подходящие идеи.',
      },
    ],
  },
];
