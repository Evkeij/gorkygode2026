// App.jsx
import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import SettingsView from './components/SettingsView';
import { initialChats } from './data/initialChats';
import './styles/global.css';

function readSetting(key, fallback) {
    try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : value;
    } catch {
        return fallback;
    }
}

function App() {
    const [chats, setChats] = useState(initialChats);
    const [activeChatId, setActiveChatId] = useState(1);
    const [page, setPage] = useState('chat');
    const [settings, setSettings] = useState(() => ({
        voiceEnabled: readSetting('descvoice-voice', 'true') === 'true',
        theme: readSetting('descvoice-theme', 'dark'),
        language: readSetting('descvoice-language', 'ru'),
    }));

    const updateSetting = (key, value) => {
        setSettings((previous) => ({
            ...previous,
            [key]: value,
        }));

        try {
            const storageKey = {
                voiceEnabled: 'descvoice-voice',
                theme: 'descvoice-theme',
                language: 'descvoice-language',
            }[key];

            localStorage.setItem(storageKey, String(value));
        } catch (error) {
            console.warn('Не удалось сохранить настройку:', error);
        }
    };

    const addMessageToActiveChat = (message) => {
        setChats((prevChats) =>
            prevChats.map((chat) =>
                chat.id === activeChatId
                    ? { ...chat, messages: [...chat.messages, message] }
                    : chat
            )
        );
    };

    const createChat = () => {
        const newChat = {
            id: Date.now(),
            title: 'Новый чат',
            messages: [],
        };

        setChats((prevChats) => [newChat, ...prevChats]);
        setActiveChatId(newChat.id);
        setPage('chat');
    };

    return (
        <main className="app-shell">
            <Sidebar
                chats={chats}
                activeChatId={activeChatId}
                page={page}
                onCreateChat={createChat}
                onSelectChat={(chatId) => {
                    setActiveChatId(chatId);
                    setPage('chat');
                }}
                onGoHome={() => setPage('chat')}
                onToggleSettings={() => {
                    setPage((currentPage) =>
                        currentPage === 'settings' ? 'chat' : 'settings'
                    );
                }}
            />

            {page === 'settings' ? (
                <SettingsView
                    settings={settings}
                    onVoiceChange={(value) => updateSetting('voiceEnabled', value)}
                    onThemeChange={(value) => updateSetting('theme', value)}
                    onLanguageChange={(value) => {
                        updateSetting('language', value);
                        import('./i18n').then(({ default: i18n }) => {
                            i18n.changeLanguage(value);
                        });
                    }}
                />
            ) : (
                <ChatWindow
                    chats={chats}
                    activeChatId={activeChatId}
                    addMessageToActiveChat={addMessageToActiveChat}
                    voiceEnabled={settings.voiceEnabled}
                    language={settings.language}
                />
            )}
        </main>
    );
}

export default App;