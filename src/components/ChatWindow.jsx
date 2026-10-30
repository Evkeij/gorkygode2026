
import { useState, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import MessageComposer from './MessageComposer';
import { sendChat } from '../api';
import '../styles/ChatWindow.css';

function ChatWindow({ chats, activeChatId, addMessageToActiveChat, voiceEnabled }) {
    const [isSending, setIsSending] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const audioRef = useRef(null);

    const activeChat = chats.find((chat) => chat.id === activeChatId);

    const stopSpeaking = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
        }
        setIsSpeaking(false);
    };

    const handleSend = async (text) => {
        if (!activeChat || isSending) return;

        const userMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
        };
        addMessageToActiveChat(userMessage);
        setIsSending(true);

        try {
            const data = await sendChat(text);
            const assistantMessage = {
                id: Date.now().toString() + 'ai',
                role: 'assistant',
                content: data.reply || "Пустой ответ",
            };
            addMessageToActiveChat(assistantMessage);

            if (data.reply && voiceEnabled && window.voiceAPI?.speak) {
                setIsSpeaking(true);
                const res = await window.voiceAPI.speak(data.reply);

                if (res.success && res.audio) {
                    const blob = new Blob([res.audio], { type: 'audio/mpeg' });
                    const url = URL.createObjectURL(blob);

                    if (audioRef.current) {
                        audioRef.current.pause();
                    }

                    const audio = new Audio(url);
                    audioRef.current = audio;

                    audio.onended = () => setIsSpeaking(false);
                    audio.onerror = () => setIsSpeaking(false);

                    audio.play().catch((e) => {
                        console.error('Ошибка воспроизведения:', e);
                        setIsSpeaking(false);
                    });
                } else {
                    console.error('Ошибка TTS:', res.error);
                    setIsSpeaking(false);
                }
            }

        } catch (error) {
            console.error('Ошибка при получении ответа:', error);
            addMessageToActiveChat({
                id: Date.now().toString() + 'err',
                role: 'assistant',
                content: 'Ошибка: не удалось связаться с сервером.',
            });
        } finally {
            setIsSending(false);
        }
    };

    useEffect(() => {
        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
            }
        };
    }, []);

    if (!activeChat) {
        return (
            <section className="workspace">
                <div className="chat-glass-panel">
                    <div className="chat-empty-state">
                        <h2>Выбери чат или создай новый</h2>
                    </div>
                </div>
            </section>
        );
    }

    return (
        <section className="workspace">
            <div className="chat-glass-panel">
                <header className="chat-header">
                    <div className="chat-header-info">
                        <h1>{activeChat.title}</h1>
                    </div>
                </header>

                <div className="chat-content">
                    <MessageList messages={activeChat.messages} />
                </div>

                <MessageComposer
                    onSend={handleSend}
                    disabled={isSending}
                    isSpeaking={isSpeaking}
                    onStopSpeaking={stopSpeaking}
                />

                <p className="chat-disclaimer">
                    DescVoice
                </p>
            </div>
        </section>
    );
}

export default ChatWindow;