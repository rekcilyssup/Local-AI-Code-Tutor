import { fetchEventSource } from '@microsoft/fetch-event-source';
import axios from 'axios';
import type { StreamChunkPayload, BackendInfo, RagSource } from '../types';

const BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_TOP_K = 2;

export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get(`${BASE_URL}/api/v1/health`, { timeout: 2000 });
    return response.status === 200 && response.data?.status === 'ok';
  } catch (error) {
    return false;
  }
};

export const getBackendInfo = async (): Promise<BackendInfo> => {
  try {
    const response = await axios.get(`${BASE_URL}/`, { timeout: 2000 });
    if (response.status === 200) {
      return response.data;
    }
  } catch (error) {
    // console.error(error);
  }
  return {};
};

export const getMentorNonStreaming = async (code: string, ragSource: RagSource = 'personal'): Promise<string> => {
  const url = `${BASE_URL}/api/v1/mentor`;
  const payload = {
    current_broken_code: code,
    top_k: DEFAULT_TOP_K,
    rag_source: ragSource
  };
  
  const response = await axios.post(url, payload, { timeout: 120000 });
  return response.data?.response || '';
};

export const streamMentorResponse = async (
  code: string,
  ragSource: RagSource = 'personal',
  onChunk: (chunk: StreamChunkPayload) => void,
  onFinish: () => void,
  onError: (err: any) => void
) => {
  const url = `${BASE_URL}/api/v1/mentor/stream`;
  const payload = {
    current_broken_code: code,
    top_k: DEFAULT_TOP_K,
    rag_source: ragSource
  };

  const ctrl = new AbortController();

  try {
    await fetchEventSource(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
      async onopen(res) {
        if (res.ok && res.headers.get('content-type')?.includes('text/event-stream')) {
          return;
        } else {
          throw new Error('Connection failed');
        }
      },
      onmessage(event) {
        const type = event.event;
        const dataStr = event.data;
        
        try {
          const data = JSON.parse(dataStr);
          if (type === 'token') {
            onChunk({ type: 'token', content: data.text || '' });
          } else if (type === 'sources') {
            onChunk({ type: 'sources', content: data.items || [] });
          } else if (type === 'metrics') {
            onChunk({ type: 'metrics', content: data });
          } else if (type === 'error') {
            onChunk({ type: 'error', content: data.message || 'Unknown error' });
          } else if (type === 'done') {
            onChunk({ type: 'done', content: data.status });
            ctrl.abort(); // Close after done
            onFinish();
          }
        } catch (e) {
          // ignore parse errors for heartbeat or empty lines
        }
      },
      onclose() {
        onFinish();
      },
      onerror(err) {
        onError(err);
        ctrl.abort();
        throw err; // prevent retrying automatically
      }
    });
  } catch (err) {
    onError(err);
  }
};
