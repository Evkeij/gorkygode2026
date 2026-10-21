import { useState } from 'react';

import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import SettingsView from './components/SettingsView';

import { initialChats } from './data/initialChats';
import './styles/global.css';

function App() {
  const [chats, setChats] = useState(initialChats);
  const [activeChatId, setActiveChatId] = useState(1);
  const [page, setPage] = useState('chat');

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
        <SettingsView />
      ) : (
        <ChatWindow
          chats={chats}
          setChats={setChats}
          activeChatId={activeChatId}
        />
      )}
    </main>
  );
}

export default App;
