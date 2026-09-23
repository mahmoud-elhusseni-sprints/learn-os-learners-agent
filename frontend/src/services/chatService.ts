import {
    Message,
    Session,
    BackendConversation,
    BackendMessage,
    BackendChatResponse,
    BackendArtifact,
    ConnectionStatus,
    VisualArtifact,
} from "../types/chat";
import {
    apiRequest,
    authenticatedRequest,
    ApiError,
    API_BASE_URL,
} from "./apiClient";
import { INITIAL_MOCK_SESSIONS } from "../data/mockConversations";

/**
 * Fallback demo user ID used only when running without authentication
 * (e.g. in offline / mock mode). Authenticated flows use the user ID
 * returned by the backend after sign-in.
 */
export const DEMO_USER_ID = Number(process.env.NEXT_PUBLIC_DEMO_USER_ID || 1);

/**
 * Generates an intelligent, domain-tailored assistant response
 * for Employer Talent Intelligence client-side previews.
 * Clearly labeled as simulation — NOT persisted to backend database.
 */
export function generateSimulatedResponse(prompt: string): string {
    const lower = prompt.toLowerCase();

    const SIMULATION_HEADER = `> ⚠️ **Simulated Intelligence Preview**  
> *This response is generated on the client for demonstration purposes. Live agent endpoint integration is pending.*

`;

    if (
        lower.includes("python") ||
        lower.includes("backend") ||
        lower.includes("neo4j") ||
        lower.includes("fastapi") ||
        lower.includes("database") ||
        lower.includes("tariq")
    ) {
        return `${SIMULATION_HEADER}### Talent Intelligence Analysis: Backend & Graph Database Competencies

**Focus Area:** Backend Architecture & Graph DB Optimization  
**Data Sources:** Synthesized Git PRs, peer reviews, and automated test coverage records

#### Verified Competencies
- **High-Concurrency Patterns:** Candidates in this domain demonstrate async task execution using FastAPI and background worker queues.
- **Graph Schema Integrity:** Implementation of deterministic constraints, idempotent \`MERGE\` patterns, and batched loading.
- **Observability:** Integration of OpenTelemetry tracing and structured JSON logging across services.

#### Suggested Follow-Up
Would you like to generate a structured technical interview scorecard focusing on high-throughput database synchronization?`;
    }

    if (
        lower.includes("alex") ||
        lower.includes("chen") ||
        lower.includes("ai") ||
        lower.includes("agent") ||
        lower.includes("llm") ||
        lower.includes("mlops")
    ) {
        return `${SIMULATION_HEADER}### Candidate Overview: Autonomous Agent Architectures

**Core Domain:** Autonomous Agent Architecture & LLM Orchestration

#### Candidate Highlights
1. **Tool-Calling Pipelines:** Multi-agent communication protocols with error fallback mechanisms.
2. **Deterministic Evaluation:** Regression suites enforcing schema validation on output models.
3. **Latency Optimization:** Parallel subagent dispatch and asynchronous execution flows.

**Next Steps:** Proceed with technical architecture review to evaluate production readiness.`;
    }

    if (
        lower.includes("react") ||
        lower.includes("frontend") ||
        lower.includes("next.js") ||
        lower.includes("ui") ||
        lower.includes("design")
    ) {
        return `${SIMULATION_HEADER}### Talent Profile: Modern Frontend Engineering

**Domain Evaluation:** React 19, Next.js App Router, Tailwind CSS, & State Decoupling

#### Verified Competencies
- **Component Architecture:** Strict decoupling between presentation components, state containers, and data services.
- **Performance:** Optimized Core Web Vitals (LCP, INP, CLS) with server-side rendering and responsive viewport optimization.
- **Design System Fidelity:** Attention to typography, accessible color contrast, and fluid transitions.

Would you like to review sample component implementations?`;
    }

    if (
        lower.includes("compare") ||
        lower.includes("vs") ||
        lower.includes("benchmark") ||
        lower.includes("candidate")
    ) {
        return `${SIMULATION_HEADER}### Candidate Comparative Benchmark

Based on verified skill cards and review turnaround metrics:

| Dimension | Primary Profile | Benchmark Profile |
| :--- | :--- | :--- |
| **Code Review Depth** | Identifies subtle race conditions and memory leaks | Focuses heavily on code style and test coverage |
| **System Resiliency** | High (automated retry loops & circuit breakers) | Moderate (standard error boundary handling) |
| **Documentation Quality** | Architecture RFCs & sequence diagrams | Concise READMEs & API specifications |

**Summary:** The primary profile demonstrates strong risk mitigation and fault-tolerant system design.`;
    }

    // Default intelligent assistant response
    return `${SIMULATION_HEADER}### Talent Intelligence Synthesis

Thank you for your prompt: *"_${prompt.trim()}_"*

Cross-referencing against learner graph records:

1. **Skill Verification:** Analyzed learner memory cards, code contribution artifacts, and architectural review logs.
2. **Alignment:** Profiles in this category exhibit strong technical grounding and self-directed problem solving.
3. **Recommendation:**
   - Review relevant evidence artifacts linked in the candidate dossier.
   - Use targeted behavioral questions regarding how they handled edge cases in previous sprint deliverables.`;
}

/**
 * Maps a raw backend message object to frontend Message interface.
 * Preserves canonical data without inventing fake candidate IDs or match scores.
 */
export function mapBackendMessage(msg: BackendMessage): Message {
    const role =
        msg.sender_role === "assistant"
            ? "assistant"
            : msg.sender_role === "system"
              ? "system"
              : "user";

    const timestamp =
        msg.timestamp || msg.created_at || new Date().toISOString();

    return {
        id:
            msg.id == null
                ? `message-${msg.sender_role}-${timestamp}`
                : String(msg.id),
        role,
        content: msg.content,
        timestamp,
        artifacts: msg.artifacts?.map(mapBackendArtifact),
    };
}

function mapBackendArtifact(artifact: BackendArtifact): VisualArtifact {
    let type: VisualArtifact["type"];
    if (artifact.format === "svg") {
        type = "svg";
    } else if (artifact.format === "html") {
        type = "container";
    } else {
        type = "image";
    }

    return {
        type,
        content: artifact.encoding === "text" ? artifact.data : undefined,
        url:
            artifact.encoding === "base64"
                ? `data:image/${artifact.format};base64,${artifact.data}`
                : undefined,
        caption: artifact.commentary,
    };
}

/**
 * Main Service Layer for Talent Intelligence Chat Operations.
 * Communicates directly with backend REST endpoints:
 * - GET/POST /users/{user_id}/conversations
 * - GET/POST /conversations/{conversation_id}/messages
 */
export const ChatService = {
    /**
     * Checks current connection status with the backend REST API.
     * Requires a valid JWT token since GET /users/{id}/conversations is protected.
     */
    async checkConnection(
        userId?: number,
        token?: string,
    ): Promise<ConnectionStatus> {
        const effectiveUserId = userId || DEMO_USER_ID;
        try {
            if (token) {
                await authenticatedRequest<BackendConversation[]>(
                    `/users/${effectiveUserId}/conversations`,
                    token,
                );
            } else {
                await apiRequest<BackendConversation[]>(
                    `/users/${effectiveUserId}/conversations`,
                );
            }
            return {
                isLiveApi: true,
                serverUrl: API_BASE_URL,
                userId: effectiveUserId,
                userName: "Authenticated Employer",
                error: null,
            };
        } catch (err: unknown) {
            const errorMsg =
                err instanceof ApiError ? err.message : String(err);
            return {
                isLiveApi: false,
                serverUrl: API_BASE_URL,
                userId: effectiveUserId,
                userName: "Demo Employer",
                error: errorMsg,
            };
        }
    },

    /**
     * Fetch all conversation sessions for a given user from the backend REST API.
     * Single-request operation: Does NOT issue N individual message requests.
     * Endpoint: GET /users/{user_id}/conversations
     *
     * This endpoint is JWT-protected. Pass the access_token from AuthContext.
     */
    async getSessions(userId?: number, token?: string): Promise<Session[]> {
        const effectiveUserId = userId || DEMO_USER_ID;

        let rawConversations: BackendConversation[];

        if (token) {
            // Authenticated request — sends Authorization: Bearer <token>
            rawConversations = await authenticatedRequest<
                BackendConversation[]
            >(`/users/${effectiveUserId}/conversations`, token);
        } else {
            // Unauthenticated fallback (offline / demo mode)
            rawConversations = await apiRequest<BackendConversation[]>(
                `/users/${effectiveUserId}/conversations`,
            );
        }

        if (!Array.isArray(rawConversations) || rawConversations.length === 0) {
            return [];
        }

        // Sort by updated_at descending (latest first)
        const sortedConversations = [...rawConversations].sort((a, b) => {
            const dateA = new Date(a.updated_at || a.created_at).getTime();
            const dateB = new Date(b.updated_at || b.created_at).getTime();
            return dateB - dateA;
        });

        // Efficient O(1) mapping without N+1 message requests
        return sortedConversations.map((conv) => ({
            id: String(conv.id),
            title: `Investigation #${conv.id}`,
            createdAt: conv.created_at,
            updatedAt: conv.updated_at || conv.created_at,
            preview: `Conversation #${conv.id}`,
            messages: [],
        }));
    },

    /**
     * Fetch all messages for a specific conversation session on demand.
     * Endpoint: GET /conversations/{conversation_id}/messages
     * Supports optional JWT authentication header.
     */
    async getMessages(
        conversationId: string | number,
        token?: string,
    ): Promise<Message[]> {
        let rawMessages: BackendMessage[];
        if (token) {
            rawMessages = await authenticatedRequest<BackendMessage[]>(
                `/conversations/${conversationId}/messages`,
                token,
            );
        } else {
            rawMessages = await apiRequest<BackendMessage[]>(
                `/conversations/${conversationId}/messages`,
            );
        }
        return Array.isArray(rawMessages)
            ? rawMessages.map(mapBackendMessage)
            : [];
    },

    /**
     * Fetch a single session by its ID with all hydrated messages.
     */
    async getSessionById(
        sessionId: string,
        token?: string,
    ): Promise<Session | null> {
        try {
            const messages = await this.getMessages(sessionId, token);
            const lastMsg = messages[messages.length - 1];

            return {
                id: sessionId,
                title: `Investigation #${sessionId}`,
                createdAt: messages[0]?.timestamp || new Date().toISOString(),
                updatedAt: lastMsg?.timestamp || new Date().toISOString(),
                preview: lastMsg ? lastMsg.content.slice(0, 70) : "No messages",
                messages,
            };
        } catch (err) {
            console.error(`Failed to fetch session #${sessionId}:`, err);
            return null;
        }
    },

    /**
     * Creates a new conversation session via backend REST API.
     * Endpoint: POST /users/{user_id}/conversations
     *
     * Supports both:
     * - createSession(userId, prompt)
     * - createSession(userId, token, prompt)
     */
    async createSession(
        userId?: number,
        tokenOrPrompt?: string,
        initialPrompt?: string,
    ): Promise<Session> {
        const effectiveUserId = userId || DEMO_USER_ID;

        let token: string | undefined;
        let prompt: string | undefined;

        if (initialPrompt !== undefined) {
            token = tokenOrPrompt;
            prompt = initialPrompt;
        } else {
            if (tokenOrPrompt && tokenOrPrompt.startsWith("eyJ")) {
                token = tokenOrPrompt;
                prompt = undefined;
            } else {
                token = undefined;
                prompt = tokenOrPrompt;
            }
        }

        let rawConversation: BackendConversation;
        if (token) {
            rawConversation = await authenticatedRequest<BackendConversation>(
                `/users/${effectiveUserId}/conversations`,
                token,
                {
                    method: "POST",
                    body: JSON.stringify({}),
                },
            );
        } else {
            rawConversation = await apiRequest<BackendConversation>(
                `/users/${effectiveUserId}/conversations`,
                {
                    method: "POST",
                    body: JSON.stringify({}),
                },
            );
        }

        const sessionId = String(rawConversation.id);
        const initialTitle = prompt
            ? prompt.slice(0, 36) + (prompt.length > 36 ? "..." : "")
            : `Investigation #${rawConversation.id}`;

        return {
            id: sessionId,
            title: initialTitle,
            createdAt: rawConversation.created_at,
            updatedAt: rawConversation.updated_at || rawConversation.created_at,
            preview: prompt || `Investigation #${rawConversation.id}`,
            messages: [],
        };
    },

    /**
     * Dispatches user prompt to backend REST API.
     * Priority:
     * 1. If authenticated with token, calls Mariam's live agent chat endpoint:
     *    POST /conversations/{conversation_id}/chat
     *    Payload: { content: prompt, learner_name_or_id?: string }
     *    Bearer Authorization header included.
     * 2. If /chat returns 404 (endpoint not present in current backend build) or no token:
     *    Falls back to POST /conversations/{conversation_id}/messages to record the
     *    user message and generates a labeled client-side preview for the assistant.
     */
    async sendMessage(
        sessionId: string,
        prompt: string,
        token?: string,
        learnerNameOrId?: string,
    ): Promise<{
        userMessage: Message;
        assistantResponse: Message;
        updatedSession: Session;
    }> {
        const convId = Number(sessionId);
        const now = new Date().toISOString();

        const localUserMessage: Message = {
            id: `msg-${Date.now()}-user`,
            role: "user",
            content: prompt.trim(),
            timestamp: now,
        };

        // Attempt 1: Call live backend agent chat endpoint (Task 20)
        if (token) {
            try {
                const agentResponse = await authenticatedRequest<
                    BackendChatResponse | BackendMessage
                >(`/conversations/${convId}/chat`, token, {
                    method: "POST",
                    body: JSON.stringify({
                        content: prompt.trim(),
                        ...(learnerNameOrId
                            ? { learner_name_or_id: learnerNameOrId }
                            : {}),
                    }),
                });

                const assistantResponse: Message =
                    "response" in agentResponse
                        ? {
                              id: String(agentResponse.message.id),
                              role: "assistant",
                              content: agentResponse.response.markdown,
                              timestamp:
                                  agentResponse.message.timestamp ||
                                  agentResponse.message.created_at ||
                                  now,
                              artifacts: agentResponse.response.artifacts?.map(
                                  (artifact) => ({
                                      id: `${agentResponse.message.id}-${artifact.format}`,
                                      ...mapBackendArtifact(artifact),
                                  }),
                              ),
                          }
                        : mapBackendMessage(agentResponse);
                assistantResponse.isSimulated = false;

                const updatedSession: Session = {
                    id: sessionId,
                    title:
                        prompt.slice(0, 36).trim() +
                        (prompt.length > 36 ? "..." : ""),
                    createdAt: localUserMessage.timestamp,
                    updatedAt: assistantResponse.timestamp,
                    preview: prompt.trim().slice(0, 70),
                    messages: [localUserMessage, assistantResponse],
                };

                return {
                    userMessage: localUserMessage,
                    assistantResponse,
                    updatedSession,
                };
            } catch (err: unknown) {
                // If it's a 404, the backend build doesn't have /chat yet; fall through to /messages fallback.
                // For 401 Unauthorized, rethrow immediately to trigger auth redirection.
                if (err instanceof ApiError && err.status === 401) {
                    throw err;
                }
                if (!(err instanceof ApiError && err.status === 404)) {
                    // If it's another error (502 bad gateway, 504 timeout, etc.), rethrow
                    throw err;
                }
                console.warn(
                    "Live agent /chat endpoint returned 404; falling back to standard /messages endpoint.",
                );
            }
        }

        // Attempt 2 / Fallback: Persist user message to POST /conversations/{id}/messages
        let userMessage = localUserMessage;
        try {
            const rawUserMsg = token
                ? await authenticatedRequest<BackendMessage>(
                      `/conversations/${convId}/messages`,
                      token,
                      {
                          method: "POST",
                          body: JSON.stringify({
                              sender_role: "user",
                              content: prompt.trim(),
                          }),
                      },
                  )
                : await apiRequest<BackendMessage>(
                      `/conversations/${convId}/messages`,
                      {
                          method: "POST",
                          body: JSON.stringify({
                              sender_role: "user",
                              content: prompt.trim(),
                          }),
                      },
                  );
            userMessage = mapBackendMessage(rawUserMsg);
        } catch (err: unknown) {
            if (err instanceof ApiError && err.status === 401) {
                throw err;
            }
            console.warn(
                "Failed to persist user message to /messages, using local copy:",
                err,
            );
        }

        // Generate simulated assistant preview
        const assistantText = generateSimulatedResponse(prompt);
        const assistantResponse: Message = {
            id: `sim-${Date.now()}`,
            role: "assistant",
            content: assistantText,
            timestamp: new Date().toISOString(),
            isSimulated: true,
        };

        const updatedSession: Session = {
            id: sessionId,
            title:
                prompt.slice(0, 36).trim() + (prompt.length > 36 ? "..." : ""),
            createdAt: userMessage.timestamp,
            updatedAt: assistantResponse.timestamp,
            preview: prompt.trim().slice(0, 70),
            messages: [userMessage, assistantResponse],
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
