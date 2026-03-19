import React from 'react';
import { CheckCircle2, XCircle, Trash2 } from 'lucide-react';
import type { BackendInfo, RagSource } from '../types';

interface SidebarProps {
  isOnline: boolean;
  backendInfo: BackendInfo | null;
  useStreaming: boolean;
  setUseStreaming: (val: boolean) => void;
  onClearChat: () => void;
  isOpen: boolean;
  ragSource: RagSource;
  setRagSource: (val: RagSource) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOnline,
  backendInfo,
  useStreaming,
  setUseStreaming,
  onClearChat,
  isOpen,
  ragSource,
  setRagSource
}) => {
  const activeModel = backendInfo?.mentor_model || 'unknown';

  return (
    <aside className="glass-panel" style={{ 
      width: isOpen ? '320px' : '0px', 
      padding: isOpen ? '1.5rem' : '0px', 
      display: 'flex', flexDirection: 'column', gap: '1.5rem', 
      borderRight: isOpen ? '1px solid var(--border-color)' : 'none', 
      height: '100vh', position: 'sticky', top: 0,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
      overflow: 'hidden',
      opacity: isOpen ? 1 : 0
    }}>
      <div style={{ padding: '1rem', backgroundColor: 'var(--panel-bg)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)', fontWeight: 500 }}>
          {isOnline ? <CheckCircle2 size={18} color="var(--success-color)" /> : <XCircle size={18} color="var(--danger-color)" />}
          Backend: {isOnline ? 'Online' : 'Offline'}
        </div>
        {isOnline ? (
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Active Model: {activeModel}</p>
        ) : (
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: 'var(--text-secondary)' }}>Ensure backend is running on port 8000.</p>
        )}
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)' }} />

      <div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.75rem', fontWeight: 500 }}>
          RAG Memory Source
        </p>
        
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', backgroundColor: '#111', padding: '0.25rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <button 
            onClick={() => setRagSource('personal')}
            style={{ 
              flex: 1, padding: '0.5rem', fontSize: '0.75rem', fontWeight: 500, border: 'none', 
              borderRadius: '4px', cursor: 'pointer', fontFamily: 'inherit',
              backgroundColor: ragSource === 'personal' ? 'var(--text-primary)' : 'transparent',
              color: ragSource === 'personal' ? '#000' : 'var(--text-secondary)',
              transition: 'all 0.2s'
            }}
          >
            My Submissions
          </button>
          <button 
            onClick={() => setRagSource('global')}
            style={{ 
              flex: 1, padding: '0.5rem', fontSize: '0.75rem', fontWeight: 500, border: 'none', 
              borderRadius: '4px', cursor: 'pointer', fontFamily: 'inherit',
              backgroundColor: ragSource === 'global' ? 'var(--text-primary)' : 'transparent',
              color: ragSource === 'global' ? '#000' : 'var(--text-secondary)',
              transition: 'all 0.2s'
            }}
          >
            Global Dataset
          </button>
        </div>

        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Model selection is controlled by backend config/terminal (MENTOR_MODEL).
        </p>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', fontSize: '0.875rem' }}>
          <input 
            type="checkbox" 
            checked={useStreaming} 
            onChange={(e) => setUseStreaming(e.target.checked)}
            style={{ width: '1rem', height: '1rem', accentColor: 'var(--accent-color)' }}
          />
          Use Streaming (SSE)
        </label>
      </div>

      <div style={{ marginTop: 'auto' }}>
        <button 
          className="btn btn-secondary" 
          onClick={onClearChat}
          style={{ width: '100%', color: 'var(--danger-color)' }}
        >
          <Trash2 size={16} /> Clear Chat History
        </button>
      </div>
    </aside>
  );
};
