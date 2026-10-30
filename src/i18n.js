import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  ru: {
    translation: {
      home: 'На главную',
      newChat: 'Новый чат',
      recentChats: 'Недавние чаты',
      settings: 'Настройки',
      emptyChat: 'Начни разговор — напиши первое сообщение.',
      you: 'Ты',

      voicePlayback: 'Озвучивание ответов',
      voiceDescription: 'Включи, чтобы ассистент зачитывал ответы вслух.',

      theme: 'Тема оформления',
      darkTheme: 'Тёмная',
      lightTheme: 'Светлая',
      themeDescription: 'Сейчас используется тёмная тема. Светлая тема появится позже.',

      language: 'Язык интерфейса',
      russian: 'Русский',
      english: 'Английский',
      languageDescription: 'Сейчас выбран русский язык.',

      comingSoon: 'Скоро появится',
      settingsTitle: 'Настройки',
    },
  },

  en: {
    translation: {
      home: 'Home',
      newChat: 'New chat',
      recentChats: 'Recent chats',
      settings: 'Settings',
      emptyChat: 'Start a conversation — write your first message.',
      you: 'You',

      voicePlayback: 'Voice playback',
      voiceDescription: 'Enable this to have the assistant read responses aloud.',

      theme: 'Appearance',
      darkTheme: 'Dark',
      lightTheme: 'Light',
      themeDescription: 'The dark theme is active. The light theme is coming soon.',

      language: 'Interface language',
      russian: 'Russian',
      english: 'English',
      languageDescription: 'English is currently selected.',

      comingSoon: 'Coming soon',
      settingsTitle: 'Settings',
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem('descvoice-language') || 'ru',
  fallbackLng: 'ru',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;