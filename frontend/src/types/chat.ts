export interface CandidateMetadata {
    candidateId?: string;
    candidateName?: string;
    role?: string;
    matchScore?: number;
    tags?: string[];
    evidenceIds?: string[];
}

export interface VisualArtifact {
    id?: string;
    type: "svg" | "image" | "card" | "chart" | "container";
    title?: string;
    content?: string; // Raw SVG or XML/HTML markup
    url?: string; // Image URL / base64 src
    caption?: string;
    metadata?: Record<string, unknown>;
}

export interface Message {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: string;
    metadata?: CandidateMetadata;
    isSimulated?: boolean;
    artifacts?: VisualArtifact[];
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

// Backend REST API Models
export interface BackendUser {
    id: number;
    name: string;
    email: string;
    created_at?: string;
    updated_at?: string;
}

export interface BackendConversation {
    id: number;
    user_id: number;
    created_at: string;
    updated_at: string;
}

export interface BackendMessage {
    id: number;
    conversation_id: number;
    sender_role: string;
    content: string;
    timestamp?: string;
    created_at?: string;
}

export interface BackendChatResponse {
    message: BackendMessage;
    response: {
        markdown: string;
        artifacts?: Array<{
            format: string;
            data: string;
            encoding: "text" | "base64";
            commentary: string;
            evidence: Array<Record<string, unknown>>;
        }>;
        fallback?: { code: string; notice: string } | null;
    };
}

export interface ConnectionStatus {
    isLiveApi: boolean;
    serverUrl: string;
    userId?: number;
    userName?: string;
    error?: string | null;
}
