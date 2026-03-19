export interface Message {
  role: 'user' | 'assistant';
  content: string;
  code?: string;
  sources?: Source[];
  metrics?: Metrics;
}

export interface Source {
  title: string;
  distance: number;
  document: string;
  lang: string;
  statusDisplay?: string;
}

export interface Metrics {
  total_request_time?: number;
  mentor_model?: string;
  [key: string]: any;
}

export interface BackendInfo {
  mentor_model?: string;
  [key: string]: any;
}

export type RagSource = 'personal' | 'global';

export type StreamChunkPayload = 
  | { type: 'token'; content: string }
  | { type: 'sources'; content: Source[] }
  | { type: 'metrics'; content: Metrics }
  | { type: 'error'; content: string }
  | { type: 'done'; content: string };
