import { Message, Session } from '../types/chat';
import { INITIAL_MOCK_SESSIONS } from '../data/mockConversations';

// In-memory store initialized from mockConversations data
let sessionStore: Session[] = JSON.parse(JSON.stringify(INITIAL_MOCK_SESSIONS));

/**
 * Generates an intelligent, domain-tailored simulated agent response
 * for Employer Talent Intelligence queries.
 */
function generateSimulatedResponse(prompt: string): string {
  const lower = prompt.toLowerCase();

  if (lower.includes('python') || lower.includes('backend') || lower.includes('neo4j') || lower.includes('fastapi') || lower.includes('database')) {
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

  if (lower.includes('alex') || lower.includes('chen') || lower.includes('ai') || lower.includes('agent') || lower.includes('llm') || lower.includes('mlops')) {
    return `### Candidate Drilldown: Alex Chen (\`cand-8821\`)

**Current Assessment Tier:** Tier 1 (Strong Hire Recommendation)  
**Core Domain:** Autonomous Agent Architecture & LLM Orchestration

#### Candidate Highlights
1. **Tool-Calling Pipelines:** Built multi-agent communication protocols with robust error fallback mechanisms.
2. **Deterministic Evaluation:** Authored regression suites enforcing zero schema hallucinations on Pydantic output models.
3. **Latency Optimization:** Implemented parallel subagent dispatch reducing end-to-end task turnaround by 42%.

**Recommendation:** Proceed directly to technical architecture evaluation; profile demonstrates high autonomy and production engineering maturity.`;
  }

  if (lower.includes('react') || lower.includes('frontend') || lower.includes('next.js') || lower.includes('ui') || lower.includes('design')) {
    return `### Talent Profile: Modern Frontend Engineering

**Domain Evaluation:** React 19, Next.js App Router, Tailwind CSS, & State Decoupling

#### Verified Competencies
- **Component Architecture:** Strict decoupling between presentation components, state containers, and data services.
- **Performance:** Optimized Core Web Vitals (LCP, INP, CLS) with server-side rendering and responsive viewport optimization.
- **Design System Fidelity:** High attention to typography, accessible color contrast, and fluid transitions.

Would you like to review sample component implementations or schedule a portfolio walkthrough?`;
  }

  if (lower.includes('compare') || lower.includes('vs') || lower.includes('benchmark') || lower.includes('candidate')) {
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
 * Service Layer for Talent Intelligence Chat Operations.
 * Fully decoupled from UI layer to allow swapping with live backend API.
 */
export const ChatService = {
  /**
   * Fetch all active sessions.
   */
  async getSessions(): Promise<Session[]> {
    // Simulate brief network latency
    await new Promise((resolve) => setTimeout(resolve, 80));
    return JSON.parse(JSON.stringify(sessionStore));
  },

  /**
   * Fetch a session by its ID.
   */
  async getSessionById(sessionId: string): Promise<Session | null> {
    await new Promise((resolve) => setTimeout(resolve, 50));
    const found = sessionStore.find((s) => s.id === sessionId);
    return found ? JSON.parse(JSON.stringify(found)) : null;
  },

  /**
   * Create a new chat session.
   */
  async createSession(title?: string, initialPrompt?: string): Promise<Session> {
    await new Promise((resolve) => setTimeout(resolve, 80));
    const now = new Date().toISOString();
    const id = `sess-${Date.now()}`;
    const generatedTitle = title || (initialPrompt ? initialPrompt.slice(0, 36) + (initialPrompt.length > 36 ? '...' : '') : 'New Investigation');

    const newSession: Session = {
      id,
      title: generatedTitle,
      createdAt: now,
      updatedAt: now,
      preview: initialPrompt || 'New candidate investigation session...',
      messages: [],
    };

    sessionStore.unshift(newSession);
    return JSON.parse(JSON.stringify(newSession));
  },

  /**
   * Dispatches a user prompt to a session, generates a simulated assistant response,
   * updates the in-memory session store, and returns both messages.
   */
  async sendMessage(sessionId: string, prompt: string): Promise<{ userMessage: Message; assistantResponse: Message; updatedSession: Session }> {
    // 400ms simulated LLM thinking delay for realistic UX
    await new Promise((resolve) => setTimeout(resolve, 400));

    let session = sessionStore.find((s) => s.id === sessionId);

    if (!session) {
      // Create session on the fly if not found
      session = await ChatService.createSession(undefined, prompt);
    }

    const timestamp = new Date().toISOString();
    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: prompt.trim(),
      timestamp,
    };

    const assistantContent = generateSimulatedResponse(prompt);
    const assistantResponse: Message = {
      id: `msg-${Date.now()}-assistant`,
      role: 'assistant',
      content: assistantContent,
      timestamp: new Date().toISOString(),
      metadata: {
        candidateId: 'cand-' + Math.floor(100 + Math.random() * 900),
        matchScore: 90 + Math.floor(Math.random() * 9),
      },
    };

    session.messages.push(userMessage, assistantResponse);
    session.updatedAt = assistantResponse.timestamp;
    session.preview = prompt.trim();

    // If the session was default-titled, give it a title from the prompt
    if (session.title === 'New Investigation' || session.title.startsWith('New Chat')) {
      session.title = prompt.slice(0, 36).trim() + (prompt.length > 36 ? '...' : '');
    }

    return {
      userMessage,
      assistantResponse,
      updatedSession: JSON.parse(JSON.stringify(session)),
    };
  },

  /**
   * Clear or reset all sessions back to initial mock state (for testing / demo reset).
   */
  async resetSessions(): Promise<Session[]> {
    sessionStore = JSON.parse(JSON.stringify(INITIAL_MOCK_SESSIONS));
    return JSON.parse(JSON.stringify(sessionStore));
  },
};
