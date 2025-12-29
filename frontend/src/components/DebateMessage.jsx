import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronUp } from 'lucide-react';
import './DebateMessage.css';

export default function DebateMessage({ message }) {
  const { role, name, content } = message;
  const [isExpanded, setIsExpanded] = useState(true);

  // Determine style based on the sender's name
  let messageClass = 'debate-message';
  let badgeClass = 'role-badge';
  
  if (role === 'user') {
    messageClass += ' user';
    badgeClass += ' user-badge';
  } else if (name?.includes('Proponent') || name?.includes('Pro')) {
    messageClass += ' pro';
    badgeClass += ' pro-badge';
  } else if (name?.includes('Critic') || name?.includes('Con')) {
    messageClass += ' con';
    badgeClass += ' con-badge';
  } else if (name?.includes('Moderator')) {
    messageClass += ' mod';
    badgeClass += ' mod-badge';
  } else {
    messageClass += ' system';
  }

  const toggleExpand = () => setIsExpanded(!isExpanded);

  return (
    <div className={messageClass}>
      <div className="message-header" onClick={toggleExpand}>
        <span className={badgeClass}>{name || (role === 'user' ? 'You' : 'System')}</span>
        <button className="toggle-btn">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      
      {isExpanded && (
        <div className="message-body markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}