import '../styles/Sidebar.css';
import Icon from './ui/Icon';

function Sidebar({
  chats,
  activeChatId,
  page,
  onCreateChat,
  onSelectChat,
  onGoHome,
  onToggleSettings,
}) {
  return (
    <aside className="sidebar glass-panel">
      <button
        className="brand"
        onClick={onGoHome}
        aria-label="На главную"
      >
        <span className="brand-icon">
          <Icon name="webhook" size={22} />
        </span>

        <span className="brand-name">DescVoice</span>
        <span className="brand-version">BETA</span>
      </button>

      <button
        className="new-chat-button"
        onClick={onCreateChat}
      >
        <span>Новый чат</span>
        <span className="shortcut">＋</span>
      </button>

      <div className="sidebar-section">
        <div className="section-label">
          <span>Недавние чаты</span>
          <span className="chat-count">{chats.length}</span>
        </div>

        <div className="chat-history">
          {chats.map((chat) => (
            <button
              key={chat.id}
              className={`history-item ${activeChatId === chat.id && page === 'chat'
                  ? 'active'
                  : ''
                }`}
              onClick={() => onSelectChat(chat.id)}
              title={chat.title}
            >
              <Icon name="message" size={21} />
              <span>{chat.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-bottom">
        <button
          className={`settings-button ${page === 'settings' ? 'active' : ''
            }`}
          onClick={onToggleSettings}
        >
          <Icon name="settings" size={21} />
          <span>Настройки</span>
          <span className="settings-indicator" />
        </button>

        <div className="profile-row">
          <div className="avatar">D</div>

          <div className="profile-info">
            <span className="profile-name">Мой ассистент</span>
            <span className="profile-status">Личный помощник</span>
          </div>

          <span className="online-dot" />
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;