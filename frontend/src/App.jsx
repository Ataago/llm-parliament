import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Debate Configuration State
  const [debateConfig, setDebateConfig] = useState({
    pro_model: "anthropic/claude-3.5-sonnet",
    con_model: "anthropic/claude-3.5-sonnet",
    moderator_model: "anthropic/claude-3.5-sonnet",
    max_rounds: 3,
    enable_tools: true,
  });

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
      // Reset config for new debate? Or keep user settings? 
      // Keeping settings is usually better UX.
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // 1. Optimistically add USER message
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // 2. Stream Response
      await api.sendMessageStream(
        currentConversationId, 
        content, 
        debateConfig, // Pass the current config here
        (eventType, event) => {
          
          if (eventType === 'message') {
            // New message from Pro/Con/Mod
            setCurrentConversation((prev) => {
                const newMsg = event.data;
                // Avoid duplicates if using React StrictMode or fast updates
                const exists = prev.messages.some(m => 
                    m.role === newMsg.role && 
                    m.name === newMsg.name && 
                    m.content === newMsg.content
                );
                if(exists) return prev;
                return { ...prev, messages: [...prev.messages, newMsg] };
            });
          } else if (eventType === 'status') {
             // Optional: Display moderator status updates (decisions) in UI
             console.log("Status update:", event.data);
          } else if (eventType === 'title') {
             loadConversations(); // Refresh list to show new title
          } else if (eventType === 'complete') {
             setIsLoading(false);
          } else if (eventType === 'error') {
             console.error('Stream error:', event.message);
             setIsLoading(false);
          }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        config={debateConfig}
        onConfigChange={setDebateConfig}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  );
}

export default App;