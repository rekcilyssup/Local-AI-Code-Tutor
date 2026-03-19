import React, { useState } from 'react';
import { X } from 'lucide-react';
import type { Source, Metrics } from '../types';

interface SourcesModalProps {
  sources: Source[];
  metrics: Metrics | null;
  onClose: () => void;
}

export const SourcesModal: React.FC<SourcesModalProps> = ({ sources, metrics, onClose }) => {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <aside className="slide-in-right glass-panel" style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: '450px', height: '100vh',
      display: 'flex', flexDirection: 'column',
      borderLeft: '1px solid var(--border-color)',
      backgroundColor: 'var(--bg-color)',
      zIndex: 1000,
      boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.5)'
    }}>
      <div style={{
        width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
        overflow: 'hidden'
      }}>
        <div style={{ 
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '1.5rem', borderBottom: '1px solid var(--border-color)'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 500 }}>RAG Database Context</h2>
          <button 
            onClick={onClose}
            style={{ 
              background: 'none', border: 'none', color: 'var(--text-secondary)',
              cursor: 'pointer', padding: '0.25rem' 
            }}
          >
            <X size={24} />
          </button>
        </div>

        <div style={{ overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {sources && sources.length > 0 && (
            <div>
              <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Retrieved Code History</h3>
              
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)' }}>
                {sources.map((src, idx) => (
                  <button
                    key={idx}
                    onClick={() => setActiveTab(idx)}
                    style={{
                      padding: '0.5rem 1rem', background: 'none',
                      border: 'none', borderBottom: activeTab === idx ? '2px solid var(--accent-color)' : '2px solid transparent',
                      color: activeTab === idx ? 'var(--text-primary)' : 'var(--text-secondary)',
                      cursor: 'pointer', fontWeight: activeTab === idx ? 600 : 400
                    }}
                  >
                    Source {idx + 1} ({src.statusDisplay || 'Unknown'})
                  </button>
                ))}
              </div>

              <div>
                <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                  <strong>Title:</strong> {sources[activeTab].title} | <strong>Distance:</strong> <code>{parseFloat(sources[activeTab].distance as any || 0).toFixed(2)}</code>
                </p>
                <pre>
                  <code className={`language-${sources[activeTab].lang || 'java'}`}>
                    {sources[activeTab].document}
                  </code>
                </pre>
              </div>
            </div>
          )}

          {metrics && (
            <div>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0 0 1.5rem 0' }} />
              <h3 style={{ marginBottom: '1rem', fontSize: '1rem', fontWeight: 500 }}>Telemetry Metrics</h3>
              <pre style={{ fontSize: '0.875rem' }}>
                <code>{JSON.stringify(metrics, null, 2)}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
