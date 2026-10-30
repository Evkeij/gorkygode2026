import { useEffect, useRef } from 'react';

function MessageList({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    });
  }, [messages]);

  if (!messages || messages.length === 0) {
    return (
      <div className="chat-empty-state">
        <p>Начни разговор — напиши первое сообщение.</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => {
        const isUser = message.role === 'user';

        return (
          <div
            key={message.id}
            className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}
          >
            {!isUser && (
              <div className="message-avatar" aria-hidden="true">
                ✦
              </div>
            )}

            <div className="message-body">
              <div className="message-author">
                {isUser ? 'Ты' : 'DescVoice'}
              </div>

              <div className="message-bubble">
                {message.content}
              </div>
            </div>
          </div>
        );
      })}

      <div ref={bottomRef} />
    </div>
  );
}

export default MessageList;