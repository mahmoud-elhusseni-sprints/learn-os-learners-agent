import { Session } from '../types/chat';

export const INITIAL_MOCK_SESSIONS: Session[] = [
  {
    id: 'sess-1',
    title: 'Senior Backend Engineer (Python & Neo4j)',
    createdAt: '2026-09-08T10:15:00.000Z',
    updatedAt: '2026-09-08T10:45:00.000Z',
    preview: 'Candidate Tariq Mansour exhibits strong knowledge of Cypher query optimization and async Python...',
    candidateTag: 'Backend / Graph',
    messages: [
      {
        id: 'msg-1-1',
        role: 'user',
        content: 'Can you evaluate candidate Tariq Mansour for the Senior Backend Engineer role? We need someone with deep Python, FastAPI, and Neo4j experience.',
        timestamp: '2026-09-08T10:15:00.000Z',
      },
      {
        id: 'msg-1-2',
        role: 'assistant',
        content: `### Candidate Assessment: Tariq Mansour

**Role Alignment:** Senior Backend Engineer (Graph & Distributed Systems)  
**Match Confidence Score:** 94%

#### Verified Technical Strengths
- **Graph Database Architecture:** 4+ years working with Neo4j. Demonstrated proficiency with Cypher query optimization, index tuning, and APOC procedures (verified from project \`kg-knowledge-pipeline\`).
- **Async Python & Microservices:** Extensive FastAPI and asyncio production experience. Designed event-driven ingestion pipelines handling ~12k events/sec.
- **Testing & Code Quality:** 92% coverage across past PR reviews with strict adherence to ruff/mypy and deterministic schema validation.

#### Potential Verification Areas
- Direct experience with multi-region Neo4j Aura Enterprise clustering vs. standalone Docker setups.

#### Recommended Next Steps
Invite Tariq to the System Architecture Deep-Dive interview focusing on graph traversal under heavy concurrent writes.`,
        timestamp: '2026-09-08T10:15:45.000Z',
        metadata: {
          candidateId: 'cand-402',
          candidateName: 'Tariq Mansour',
          role: 'Senior Backend Engineer',
          matchScore: 94,
          tags: ['Python', 'FastAPI', 'Neo4j', 'Cypher', 'Distributed Systems'],
        },
      },
      {
        id: 'msg-1-3',
        role: 'user',
        content: 'How does his graph query optimization compare to our requirements for high-concurrency ingestion?',
        timestamp: '2026-09-08T10:42:00.000Z',
      },
      {
        id: 'msg-1-4',
        role: 'assistant',
        content: `Based on verified evidence from his recent sprint deliverables:

1. **Query Tuning:** Tariq refactored recursive Cypher path queries into parameterized subqueries using \`CALL { ... } IN TRANSACTIONS\`, reducing p99 latency by 68%.
2. **Batch Ingestion:** He implemented deterministic UUIDv5 node generation and batch chunking (1,000 rows/batch) to avoid transaction log exhaustion in Neo4j.
3. **Idempotency:** Implemented \`MERGE\` patterns with index-backed unique constraint lookups to guarantee atomic, replay-safe loads.

**Conclusion:** His engineering approach directly aligns with your requirements for idempotent, high-concurrency ingestion pipelines.`,
        timestamp: '2026-09-08T10:45:00.000Z',
        metadata: {
          candidateId: 'cand-402',
          candidateName: 'Tariq Mansour',
          role: 'Senior Backend Engineer',
          matchScore: 94,
          tags: ['Batch Ingestion', 'UUIDv5', 'Idempotency'],
        },
      },
    ],
  },
  {
    id: 'sess-2',
    title: 'Candidate Profile: Alex Chen (AI & MLOps)',
    createdAt: '2026-09-07T14:20:00.000Z',
    updatedAt: '2026-09-07T15:05:00.000Z',
    preview: 'Alex has verified experience building LLM tool-calling loops and offline regression suites...',
    candidateTag: 'MLOps / AI',
    messages: [
      {
        id: 'msg-2-1',
        role: 'user',
        content: 'What are the key technical highlights and risk factors for candidate Alex Chen?',
        timestamp: '2026-09-07T14:20:00.000Z',
      },
      {
        id: 'msg-2-2',
        role: 'assistant',
        content: `### Candidate Intelligence Report: Alex Chen

**Candidate ID:** \`cand-8821\`  
**Target Role:** AI Platform Engineer & Agentic Systems  
**Evaluation Status:** Verified via code artifact inspection

#### Key Technical Highlights
- **Agentic Architectures:** Authored autonomous agent loops utilizing Pydantic structured outputs and constrained function calling.
- **Evaluation Harnesses:** Established offline regression suites mocking model calls to validate parser robustness without external API latency.
- **Vector & Hybrid Search:** Integrated hybrid vector + lexical retrieval pipelines with automated recall benchmarking.

#### Identified Verification Points
- Primary deployments were serverless container environments (AWS ECS / Modal); assess on-premise Kubernetes cluster management if required for your infrastructure.

**Verdict:** High-priority candidate for the Autonomous Agent Platform team.`,
        timestamp: '2026-09-07T14:21:10.000Z',
        metadata: {
          candidateId: 'cand-8821',
          candidateName: 'Alex Chen',
          role: 'AI Platform Engineer',
          matchScore: 91,
          tags: ['LLM Agents', 'LangChain', 'Pydantic', 'FastAPI', 'MLOps'],
        },
      },
    ],
  },
  {
    id: 'sess-3',
    title: 'Tech Lead Benchmark: Distributed Systems',
    createdAt: '2026-09-05T09:00:00.000Z',
    updatedAt: '2026-09-05T09:40:00.000Z',
    preview: 'Comparative analysis of top candidates for technical leadership and architectural governance...',
    candidateTag: 'Leadership',
    messages: [
      {
        id: 'msg-3-1',
        role: 'user',
        content: 'Compare our top two candidates for the Technical Lead role regarding architectural leadership and code review quality.',
        timestamp: '2026-09-05T09:00:00.000Z',
      },
      {
        id: 'msg-3-2',
        role: 'assistant',
        content: `### Leadership Benchmark Comparison

| Evaluation Vector | Elena Rostova (\`cand-104\`) | Marcus Vance (\`cand-219\`) |
| :--- | :--- | :--- |
| **Architecture Governance** | Spearheaded RFC reviews for 4 core services; defined strict schema evolution policies | Led migration from monolith to Kubernetes; authored org-wide coding guidelines |
| **Mentorship & Code Reviews** | High review ratio (average turnaround < 4 hours), documented constructive feedback | Conducted weekly architecture guild sessions and pair-programming sprints |
| **Execution Cadence** | High emphasis on automated CI verification & deterministic builds | Fast release velocity with progressive canary rollouts |

**Recommendation:** Elena provides stronger alignment if your team prioritizes rigorous architectural governance and graph schema integrity.`,
        timestamp: '2026-09-05T09:01:25.000Z',
        metadata: {
          role: 'Tech Lead / Architect',
          matchScore: 96,
          tags: ['Architecture', 'Leadership', 'Code Review', 'RFCs'],
        },
      },
    ],
  },
];

export { ChatService } from '../services/chatService';
