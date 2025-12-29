import { useState, useEffect, useRef } from 'react';
import DebateMessage from './DebateMessage';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages]); // Only scroll when messages change

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <div className="empty-icon">🏛️</div>
          <h2>Welcome to the House</h2>
          <p>Create a new session to begin the debate.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📜</div>
            <h2>Table a Motion</h2>
            <p>Enter a topic below to start the parliamentary session.</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <DebateMessage key={index} message={msg} />
          ))
        )}

        {isLoading && (
          <div className="typing-indicator">
            <span>The Council is deliberating...</span>
            <div className="dots">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Only show input if it's the start (Round 0) or if the debate is finished (Optional feature) */}
      {/* For this MVP, we allow input only at start to kick off the auto-loop */}
      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="Proposed Motion: e.g., 'Artificial Intelligence will do more harm than good.'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Start Debate
          </button>
        </form>
      )}
    </div>
  );
}