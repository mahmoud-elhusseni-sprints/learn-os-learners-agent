export interface CandidateMetadata {
  candidateId?: string;
  candidateName?: string;
  role?: string;
  matchScore?: number;
  tags?: string[];
  evidenceIds?: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: CandidateMetadata;
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  preview?: string;
  messages: Message[];
  candidateTag?: string;
}
