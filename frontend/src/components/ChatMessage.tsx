import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Terminal, Bot, ChevronDown, ChevronRight, BarChart2 } from 'lucide-react';
import type { Message } from '../types';

interface ChatMessageProps {
  message: Message;
  onShowContext: (sources: any[], metrics: any) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onShowContext }) => {
  const isUser = message.role === 'user';
  const [showCode, setShowCode] = useState(false);

  return (
    <div style={{ 
      display: 'flex', 
      gap: '1rem', 
      padding: '1.5rem', 
      backgroundColor: isUser ? 'transparent' : 'rgba(22, 27, 34, 0.4)',
      borderBottom: '1px solid rgba(48, 54, 61, 0.3)',
      width: '100%'
    }}>
      <div style={{ 
        width: '36px', 
        height: '36px', 
        borderRadius: '8px', 
        backgroundColor: isUser ? '#2f81f7' : '#238636',
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexShrink: 0
      }}>
        {isUser ? <Terminal size={20} color="#fff" /> : <Bot size={20} color="#fff" />}
      </div>
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
          {isUser ? 'You' : 'AI Mentor'}
        </p>

        {isUser && message.code && (
          <div>
            <button 
              onClick={() => setShowCode(!showCode)}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.5rem', 
                background: 'none', border: 'none', color: 'var(--text-secondary)',
                cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.875rem',
                padding: '0.25rem 0'
              }}
            >
              {showCode ? <ChevronDown size={16} /> : <ChevronRight size={16} />} 
              View submitted code
            </button>
            {showCode && (
              <pre style={{ marginTop: '0.5rem' }}>
                <code className="language-java">{message.code}</code>
              </pre>
            )}
          </div>
        )}

        {!isUser && (
          <div className="markdown-body" style={{ color: 'var(--text-primary)', fontSize: '0.9375rem' }}>
            {message.content ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', height: '24px' }}>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            )}
          </div>
        )}

        {((message.sources && message.sources.length > 0) || message.metrics) && (
          <div style={{ marginTop: '1rem' }}>
            <button 
              className="btn btn-secondary"
              onClick={() => onShowContext(message.sources || [], message.metrics)}
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
            >
              <BarChart2 size={14} /> View Sources & Metrics
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
