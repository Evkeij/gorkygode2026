import { useState } from 'react';
import MessageList from './MessageList';
import MessageComposer from './MessageComposer';
import { getDemoResponse } from '../data/demoResponses';
import '../styles/ChatWindow.css';

function ChatWindow({ chats, setChats, activeChatId }) {
  const [isSending, setIsSending] = useState(false);

  const activeChat = chats.find(
    (chat) => chat.id === activeChatId
  );

  const handleSend = (text) => {
    if (!activeChat || isSending) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    };

    const assistantMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: getDemoResponse(text),
    };

    setIsSending(true);

    setChats((previousChats) =>
      previousChats.map((chat) => {
        if (chat.id !== activeChatId) {
          return chat;
        }

        const isNewChat = chat.messages.length === 0;

        return {
          ...chat,
          title: isNewChat ? text.slice(0, 36) : chat.title,
          messages: [
            ...chat.messages,
            userMessage,
            assistantMessage,
          ],
        };
      })
    );

    setIsSending(false);
  };

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
        />

        <p className="chat-disclaimer">
          DescVoice пока использует заранее подготовленные ответы.
        </p>
      </div>
    </section>
  );
}

export default ChatWindow;