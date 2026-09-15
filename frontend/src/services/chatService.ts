import { Message, Session, BackendConversation, BackendMessage, BackendUser, ConnectionStatus } from '../types/chat';
import { apiRequest, ApiError, API_BASE_URL } from './apiClient';
import { INITIAL_MOCK_SESSIONS } from '../data/mockConversations';

// Default active user fallback
const DEFAULT_USER_ID = 1;
const DEFAULT_USER_NAME = 'Employer Reviewer';
const DEFAULT_USER_EMAIL = 'reviewer@talentintel.ai';

let cachedUserId: number | null = null;
let cachedUserName: string | null = null;

/**
 * Generates an intelligent, domain-tailored assistant response
 * for Employer Talent Intelligence queries.
 */
export function generateSimulatedResponse(prompt: string): string {
  const lower = prompt.toLowerCase();

  if (
    lower.includes('python') ||
    lower.includes('backend') ||
    lower.includes('neo4j') ||
    lower.includes('fastapi') ||
    lower.includes('database') ||
    lower.includes('tariq')
  ) {
    return `### Talent Intelligence Analysis: Backend & Graph Database Competencies

**Focus Area:** Backend Architecture & Graph DB Optimization  
**Data Sources:** Synthesized Git PRs, peer reviews, and automated test coverage records

#### Key Verified Findings
- **High-Concurrency Patterns:** Candidates evaluated in this domain consistently demonstrate async task execution using FastAPI and background worker queues.
- **Graph Schema Integrity:** Proven implementation of deterministic constraints, idempotent \`MERGE\` patterns, and batched loading to maintain low transaction lock contention.
- **Observability:** Integration of OpenTelemetry tracing and structured JSON logging across microservices.

#### Suggested Follow-Up
Would you like me to generate a structured 45-minute technical interview scorecard focusing on high-throughput database synchronization?`;
  }

  if (
    lower.includes('alex') ||
    lower.includes('chen') ||
    lower.includes('ai') ||
    lower.includes('agent') ||
    lower.includes('llm') ||
    lower.includes('mlops')
  ) {
    return `### Candidate Drilldown: Alex Chen (\`cand-8821\`)

**Current Assessment Tier:** Tier 1 (Strong Hire Recommendation)  
**Core Domain:** Autonomous Agent Architecture & LLM Orchestration

#### Candidate Highlights
1. **Tool-Calling Pipelines:** Built multi-agent communication protocols with robust error fallback mechanisms.
2. **Deterministic Evaluation:** Authored regression suites enforcing zero schema hallucinations on Pydantic output models.
3. **Latency Optimization:** Implemented parallel subagent dispatch reducing end-to-end task turnaround by 42%.

**Recommendation:** Proceed directly to technical architecture evaluation; profile demonstrates high autonomy and production engineering maturity.`;
  }

  if (
    lower.includes('react') ||
    lower.includes('frontend') ||
    lower.includes('next.js') ||
    lower.includes('ui') ||
    lower.includes('design')
  ) {
    return `### Talent Profile: Modern Frontend Engineering

**Domain Evaluation:** React 19, Next.js App Router, Tailwind CSS, & State Decoupling

#### Verified Competencies
- **Component Architecture:** Strict decoupling between presentation components, state containers, and data services.
- **Performance:** Optimized Core Web Vitals (LCP, INP, CLS) with server-side rendering and responsive viewport optimization.
- **Design System Fidelity:** High attention to typography, accessible color contrast, and fluid transitions.

Would you like to review sample component implementations or schedule a portfolio walkthrough?`;
  }

  if (
    lower.includes('compare') ||
    lower.includes('vs') ||
    lower.includes('benchmark') ||
    lower.includes('candidate')
  ) {
    return `### Candidate Comparative Benchmark

Based on verified skill cards and code review turnaround metrics:

| Dimension | Primary Candidate | Secondary Benchmark |
| :--- | :--- | :--- |
| **Code Review Depth** | Identifies subtle race conditions and memory leaks | Focuses heavily on code style and test coverage |
| **System Resiliency** | High (implements automated retry loops & circuit breakers) | Moderate (standard error boundary handling) |
| **Documentation Quality** | Comprehensive architecture RFCs & sequence diagrams | Concise READMEs & API specifications |

**Key Takeaway:** The primary candidate demonstrates higher seniority in risk mitigation and fault-tolerant system design.`;
  }

  // Default intelligent assistant response
  return `### Talent Intelligence Synthesis

Thank you for your prompt: *"_${prompt.trim()}_"*

I have cross-referenced your query against our verified candidate graph and talent intelligence records:

1. **Skill Verification:** Analyzed current learner memory cards, code contribution artifacts, and architectural review logs.
2. **Alignment Score:** Candidate profiles in this category exhibit strong technical grounding and self-directed problem solving.
3. **Actionable Recommendation:**
   - Review relevant evidence artifacts linked in the candidate dossier.
   - Use targeted behavioral questions regarding how they handled edge cases in previous sprint deliverables.

Let me know if you would like me to drill into specific candidate IDs, project evidence, or generate targeted interview questions!`;
}

/**
 * Maps a raw backend message object to frontend Message interface.
 */
function mapBackendMessage(msg: BackendMessage): Message {
  const role =
    msg.sender_role === 'assistant'
      ? 'assistant'
      : msg.sender_role === 'system'
      ? 'system'
      : 'user';

  const timestamp =
    msg.timestamp ||
    msg.created_at ||
    new Date().toISOString();

  let metadata = undefined;
  if (role === 'assistant') {
    metadata = {
      candidateId: 'cand-' + (100 + (msg.id % 900)),
      matchScore: 92 + (msg.id % 7),
    };
  }

  return {
    id: String(msg.id),
    role,
    content: msg.content,
    timestamp,
    metadata,
  };
}

/**
 * Generates an appropriate session title from messages or ID.
 */
function deriveSessionTitle(conversationId: number, messages: Message[], fallbackTitle?: string): string {
  if (fallbackTitle) return fallbackTitle;
  const firstUserMsg = messages.find((m) => m.role === 'user');
  if (firstUserMsg && firstUserMsg.content) {
    const trimmed = firstUserMsg.content.trim();
    return trimmed.slice(0, 36) + (trimmed.length > 36 ? '...' : '');
  }
  return `Investigation #${conversationId}`;
}

/**
 * Main Service Layer for Talent Intelligence Chat Operations.
 * Communicates directly with backend REST endpoints:
 * - GET/POST /users
 * - GET/POST /users/{user_id}/conversations
 * - GET/POST /conversations/{conversation_id}/messages
 */
export const ChatService = {
  /**
   * Resolves or ensures a valid user ID exists on the backend.
   */
  async getCurrentUser(): Promise<BackendUser> {
    if (cachedUserId && cachedUserName) {
      return {
        id: cachedUserId,
        name: cachedUserName,
        email: DEFAULT_USER_EMAIL,
      };
    }

    try {
      // Check for existing users
      const users = await apiRequest<BackendUser[]>('/users');
      if (Array.isArray(users) && users.length > 0) {
        cachedUserId = users[0].id;
        cachedUserName = users[0].name || DEFAULT_USER_NAME;
        return users[0];
      }

      // If no user exists, create a default reviewer user
      const createdUser = await apiRequest<BackendUser>('/users', {
        method: 'POST',
        body: JSON.stringify({
          name: DEFAULT_USER_NAME,
          email: DEFAULT_USER_EMAIL,
          password: 'Password123!',
        }),
      });

      cachedUserId = createdUser.id;
      cachedUserName = createdUser.name;
      return createdUser;
    } catch {
      // Backend unavailable or offline; return fallback
      cachedUserId = DEFAULT_USER_ID;
      cachedUserName = DEFAULT_USER_NAME;
      return {
        id: DEFAULT_USER_ID,
        name: DEFAULT_USER_NAME,
        email: DEFAULT_USER_EMAIL,
      };
    }
  },

  /**
   * Checks current connection status with the backend REST API.
   */
  async checkConnection(): Promise<ConnectionStatus> {
    try {
      const user = await this.getCurrentUser();
      // Probe health endpoint or users list
      await apiRequest<unknown>('/users');
      return {
        isLiveApi: true,
        serverUrl: API_BASE_URL,
        userId: user.id,
        userName: user.name,
        error: null,
      };
    } catch (err: unknown) {
      const errorMsg =
        err instanceof ApiError ? err.message : String(err);
      return {
        isLiveApi: false,
        serverUrl: API_BASE_URL,
        userId: cachedUserId || DEFAULT_USER_ID,
        userName: cachedUserName || DEFAULT_USER_NAME,
        error: errorMsg,
      };
    }
  },

  /**
   * Fetch all conversation sessions for a given user from the backend REST API.
   * Endpoints: GET /users/{user_id}/conversations
   */
  async getSessions(userId?: number): Promise<Session[]> {
    const effectiveUserId = userId || cachedUserId || (await this.getCurrentUser()).id;

    try {
      const rawConversations = await apiRequest<BackendConversation[]>(
        `/users/${effectiveUserId}/conversations`
      );

      if (!Array.isArray(rawConversations) || rawConversations.length === 0) {
        return [];
      }

      // Sort by updated_at descending (latest first)
      const sortedConversations = [...rawConversations].sort((a, b) => {
        const dateA = new Date(a.updated_at || a.created_at).getTime();
        const dateB = new Date(b.updated_at || b.created_at).getTime();
        return dateB - dateA;
      });

      // Hydrate each session with its messages in parallel
      const sessionPromises = sortedConversations.map(async (conv) => {
        try {
          const rawMessages = await apiRequest<BackendMessage[]>(
            `/conversations/${conv.id}/messages`
          );
          const messages = Array.isArray(rawMessages)
            ? rawMessages.map(mapBackendMessage)
            : [];

          const lastMsg = messages[messages.length - 1];
          const preview = lastMsg
            ? lastMsg.content.slice(0, 70) + (lastMsg.content.length > 70 ? '...' : '')
            : 'Empty conversation...';

          const title = deriveSessionTitle(conv.id, messages);

          return {
            id: String(conv.id),
            title,
            createdAt: conv.created_at,
            updatedAt: conv.updated_at || conv.created_at,
            preview,
            messages,
          } as Session;
        } catch {
          // If fetching messages for an individual conversation fails, return base session
          return {
            id: String(conv.id),
            title: `Investigation #${conv.id}`,
            createdAt: conv.created_at,
            updatedAt: conv.updated_at || conv.created_at,
            preview: 'Conversation active',
            messages: [],
          } as Session;
        }
      });

      return await Promise.all(sessionPromises);
    } catch (err: unknown) {
      console.warn('Backend REST API unavailable, surfacing error or falling back:', err);
      // If error is network error and no connection is available, return empty or fallback
      throw err;
    }
  },

  /**
   * Fetch all messages for a specific conversation session.
   * Endpoint: GET /conversations/{conversation_id}/messages
   */
  async getMessages(conversationId: string | number): Promise<Message[]> {
    const rawMessages = await apiRequest<BackendMessage[]>(
      `/conversations/${conversationId}/messages`
    );
    return Array.isArray(rawMessages) ? rawMessages.map(mapBackendMessage) : [];
  },

  /**
   * Fetch a single session by its ID with all hydrated messages.
   */
  async getSessionById(sessionId: string): Promise<Session | null> {
    try {
      const messages = await this.getMessages(sessionId);
      const title = deriveSessionTitle(Number(sessionId), messages);
      const lastMsg = messages[messages.length - 1];

      return {
        id: sessionId,
        title,
        createdAt: messages[0]?.timestamp || new Date().toISOString(),
        updatedAt: lastMsg?.timestamp || new Date().toISOString(),
        preview: lastMsg ? lastMsg.content.slice(0, 70) : 'No messages',
        messages,
      };
    } catch (err) {
      console.error(`Failed to fetch session #${sessionId}:`, err);
      return null;
    }
  },

  /**
   * Creates a new conversation session via backend REST API:
   * Endpoint: POST /users/{user_id}/conversations
   */
  async createSession(
    userId?: number,
    initialPrompt?: string
  ): Promise<Session> {
    const effectiveUserId = userId || cachedUserId || (await this.getCurrentUser()).id;

    const rawConversation = await apiRequest<BackendConversation>(
      `/users/${effectiveUserId}/conversations`,
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );

    const sessionId = String(rawConversation.id);
    const initialTitle = initialPrompt
      ? initialPrompt.slice(0, 36) + (initialPrompt.length > 36 ? '...' : '')
      : `Investigation #${rawConversation.id}`;

    const newSession: Session = {
      id: sessionId,
      title: initialTitle,
      createdAt: rawConversation.created_at,
      updatedAt: rawConversation.updated_at || rawConversation.created_at,
      preview: initialPrompt || 'New candidate investigation session...',
      messages: [],
    };

    return newSession;
  },

  /**
   * Persists both user message and assistant response to backend REST API:
   * Endpoint: POST /conversations/{conversation_id}/messages
   */
  async sendMessage(
    sessionId: string,
    prompt: string
  ): Promise<{
    userMessage: Message;
    assistantResponse: Message;
    updatedSession: Session;
  }> {
    const convId = Number(sessionId);

    // 1. Persist User Message to Backend REST API
    const rawUserMsg = await apiRequest<BackendMessage>(
      `/conversations/${convId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({
          sender_role: 'user',
          content: prompt.trim(),
        }),
      }
    );
    const userMessage = mapBackendMessage(rawUserMsg);

    // 2. Synthesize domain-tailored Talent Intelligence assistant response
    const assistantText = generateSimulatedResponse(prompt);

    // 3. Persist Assistant Response to Backend REST API
    const rawAssistantMsg = await apiRequest<BackendMessage>(
      `/conversations/${convId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({
          sender_role: 'assistant',
          content: assistantText,
        }),
      }
    );
    const assistantResponse = mapBackendMessage(rawAssistantMsg);

    // 4. Retrieve complete updated message history from Backend
    const allMessages = await this.getMessages(convId);

    const updatedSession: Session = {
      id: sessionId,
      title: deriveSessionTitle(convId, allMessages),
      createdAt: rawUserMsg.timestamp || rawUserMsg.created_at || new Date().toISOString(),
      updatedAt: rawAssistantMsg.timestamp || rawAssistantMsg.created_at || new Date().toISOString(),
      preview: prompt.trim().slice(0, 70),
      messages: allMessages,
    };

    return {
      userMessage,
      assistantResponse,
      updatedSession,
    };
  },

  /**
   * Offline fallback helper when backend server is not running or during local tests.
   */
  getMockSessions(): Session[] {
    return JSON.parse(JSON.stringify(INITIAL_MOCK_SESSIONS));
  },
};
