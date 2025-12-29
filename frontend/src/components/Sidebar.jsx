import React from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  config,
  onConfigChange
}) {
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    onConfigChange({
      ...config,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Parliament</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Debate Session
        </button>
      </div>

      <div className="sidebar-config">
        <h3>Debate Configuration</h3>
        
        <div className="config-group">
          <label>Government (Pro) Model</label>
          <input 
            type="text" 
            name="pro_model" 
            value={config.pro_model} 
            onChange={handleChange} 
            placeholder="e.g. anthropic/claude-3.5-sonnet"
          />
        </div>

        <div className="config-group">
          <label>Opposition (Con) Model</label>
          <input 
            type="text" 
            name="con_model" 
            value={config.con_model} 
            onChange={handleChange}
            placeholder="e.g. anthropic/claude-3.5-sonnet"
          />
        </div>

        <div className="config-group">
          <label>Speaker (Moderator) Model</label>
          <input 
            type="text" 
            name="moderator_model" 
            value={config.moderator_model} 
            onChange={handleChange}
            placeholder="e.g. google/gemini-flash-1.5"
          />
        </div>

        <div className="config-row">
          <div className="config-group small">
            <label>Max Rounds</label>
            <input 
              type="number" 
              name="max_rounds" 
              value={config.max_rounds} 
              onChange={handleChange}
              min="1"
              max="10"
            />
          </div>
          <div className="config-group checkbox">
            <label>
              <input 
                type="checkbox" 
                name="enable_tools" 
                checked={config.enable_tools} 
                onChange={handleChange}
              />
              Enable Research Tools
            </label>
          </div>
        </div>
      </div>

      <div className="conversation-list-header">History</div>
      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No past debates</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Debate'}
              </div>
              <div className="conversation-meta">
                {new Date(conv.created_at).toLocaleDateString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}