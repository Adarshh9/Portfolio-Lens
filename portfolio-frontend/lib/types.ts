export type InteractionMode = 'recruiter' | 'engineer' | 'ama';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  mode?: InteractionMode;
  judgeScore?: JudgeScore;
  timestamp: Date;
}

export interface JudgeScore {
  grounding_score: number;
  consistency_score: number;
  depth_score: number;
  revision_required: boolean;
  feedback: string[];
  citations_used: string[];
}

export interface ChatRequest {
  message: string;
  mode?: InteractionMode;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  mode: string;
  judge_score?: JudgeScore | null;
  sources: string[];
}
