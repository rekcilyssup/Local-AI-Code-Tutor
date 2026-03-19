import React, { useEffect, useState, useRef } from 'react';
import { Send, Terminal, Menu } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { SourcesModal } from './components/SourcesModal';
import { checkHealth, getBackendInfo, getMentorNonStreaming, streamMentorResponse } from './services/api';
import type { Message, BackendInfo, Source, Metrics, RagSource } from './types';

function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [backendInfo, setBackendInfo] = useState<BackendInfo | null>(null);
  const [useStreaming, setUseStreaming] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalSources, setModalSources] = useState<Source[]>([]);
  const [modalMetrics, setModalMetrics] = useState<Metrics | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [ragSource, setRagSource] = useState<RagSource>('personal');

  const formatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const init = async () => {
      const online = await checkHealth();
      setIsOnline(online);
      if (online) {
        const info = await getBackendInfo();
        setBackendInfo(info);
      }
    };
    init();
    const interval = setInterval(init, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (formatRef.current) {
      formatRef.current.scrollTop = formatRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || !isOnline || isLoading) return;

    const userCode = inputValue;
    setInputValue('');
    
    const newUserMsg: Message = { role: 'user', content: '', code: userCode };
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    if (!useStreaming) {
      // Non-streaming
      const startTime = performance.now();
      try {
        const responseText = await getMentorNonStreaming(userCode, ragSource);
        const elapsed = Number(((performance.now() - startTime) / 1000).toFixed(2));
        
        const assistantMsg: Message = {
          role: 'assistant',
          content: responseText,
          metrics: { total_request_time: elapsed, mentor_model: backendInfo?.mentor_model || 'unknown' }
        };
        setMessages(prev => [...prev, assistantMsg]);
        setIsLoading(false);
      } catch (err) {
        setMessages(prev => [...prev, { role: 'assistant', content: '**Error**: Failed to get response from backend.' }]);
        setIsLoading(false);
      }
    } else {
      // Streaming
      let currentText = '';
      let currentSources: Source[] = [];
      let currentMetrics: Metrics | undefined = undefined;
      
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      streamMentorResponse(
        userCode,
        ragSource,
        (chunk) => {
          if (chunk.type === 'token') {
            currentText += chunk.content;
            setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], content: currentText };
              return newMsgs;
            });
          } else if (chunk.type === 'sources') {
            currentSources = chunk.content;
            setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], sources: currentSources };
              return newMsgs;
            });
          } else if (chunk.type === 'metrics') {
            currentMetrics = chunk.content;
            setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], metrics: currentMetrics };
              return newMsgs;
            });
          } else if (chunk.type === 'error') {
            setMessages(prev => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], content: currentText + `\n\n**Error:** ${chunk.content}` };
              return newMsgs;
            });
          }
        },
        () => {
          setIsLoading(false);
        },
        () => {
          setIsLoading(false);
        }
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const openContext = (sources: Source[], metrics: Metrics) => {
    setModalSources(sources);
    setModalMetrics(metrics);
    setModalOpen(true);
  };

  return (
    <div id="root">
      <Sidebar 
        isOnline={isOnline} 
        backendInfo={backendInfo} 
        useStreaming={useStreaming} 
        setUseStreaming={setUseStreaming}
        onClearChat={() => setMessages([])}
        isOpen={isSidebarOpen}
        ragSource={ragSource}
        setRagSource={setRagSource}
      />
      
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', position: 'relative' }}>
        <header style={{ 
          padding: '1.5rem 2rem', borderBottom: '1px solid var(--border-color)', 
          backgroundColor: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(12px)',
          position: 'sticky', top: 0, zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
              className="btn btn-secondary" 
              style={{ width: '40px', height: '40px', padding: 0, border: '1px solid var(--border-color)', borderRadius: '8px', background: 'var(--panel-bg)' }}
            >
              <Menu size={20} color="var(--text-primary)" />
            </button>
            <div>
              <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: 0, fontSize: '1.5rem' }}>
                AI Code Mentor
              </h1>
              <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 0 0', fontSize: '0.875rem' }}>
                Model is controlled by backend runtime. Paste your code below.
              </p>
            </div>
          </div>
        </header>

        <div 
          ref={formatRef}
          style={{ 
            flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column',
            paddingBottom: '2rem'
          }}
        >
          {messages.length === 0 ? (
            <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-secondary)', opacity: 0.5 }}>
              <Terminal size={64} style={{ marginBottom: '1rem' }} />
              <h2>No messages yet</h2>
              <p>Start by pasting your Java code below.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} onShowContext={openContext} />
            ))
          )}
        </div>

        <div style={{ padding: '2rem', borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
          <form 
            onSubmit={handleSubmit}
            style={{ 
              display: 'flex', gap: '1rem', alignItems: 'flex-end', 
              maxWidth: '1200px', margin: '0 auto', position: 'relative' 
            }}
          >
            <textarea
              className="input-base"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isOnline || isLoading}
              placeholder={isOnline ? "Paste your Java code here... (Shift+Enter to submit)" : "Backend offline. Start the FastAPI server first."}
              style={{ flex: 1, minHeight: '60px', maxHeight: '300px', resize: 'vertical' }}
              rows={3}
            />
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={!isOnline || isLoading || !inputValue.trim()}
              style={{ padding: '0.75rem 1.5rem', height: '60px' }}
            >
              <Send size={20} />
              <span>Submit</span>
            </button>
          </form>
        </div>
      </main>

      {modalOpen && (
        <SourcesModal 
          sources={modalSources} 
          metrics={modalMetrics} 
          onClose={() => setModalOpen(false)} 
        />
      )}
    </div>
  );
}

export default App;
