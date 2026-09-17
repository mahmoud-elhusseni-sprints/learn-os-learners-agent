/**
 * Comprehensive Verification Test Suite for Task 16:
 * - Real shared validation module tests (src/lib/validation.ts)
 * - apiRequest HTTP client & error mapping tests with stubbed fetch
 * - ChatService REST integration & persistence verification
 * - Client-side simulation labeling and absence of fake metadata
 */

import assert from 'node:assert';
import {
  validateName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
  validateTerms,
  getPasswordStrength,
} from '../lib/validation';
import { apiRequest, ApiError, API_BASE_URL } from '../services/apiClient';
import {
  ChatService,
  DEMO_USER_ID,
  generateSimulatedResponse,
  mapBackendMessage,
} from '../services/chatService';
import { BackendConversation, BackendMessage } from '../types/chat';

console.log('🧪 Starting Task 16 Comprehensive Verification Suite...\n');

// =========================================================================
// 1. Shared Client-Side Validation Module Tests
// =========================================================================
console.log('▶ [1/4] Testing Shared Validation Module (src/lib/validation.ts)');

// Name
assert.strictEqual(validateName(''), 'Full name is required');
assert.strictEqual(validateName('   '), 'Full name is required');
assert.strictEqual(validateName('A'), 'Name must be at least 2 characters long');
assert.strictEqual(validateName('Al'), undefined);
assert.strictEqual(validateName('Sarah Nader'), undefined);

// Email
assert.strictEqual(validateEmail(''), 'Email address is required');
assert.strictEqual(validateEmail('   '), 'Email address is required');
assert.strictEqual(validateEmail('not-an-email'), 'Please enter a valid email address (e.g., user@example.com)');
assert.strictEqual(validateEmail('missing@domain'), 'Please enter a valid email address (e.g., user@example.com)');
assert.strictEqual(validateEmail('@domain.com'), 'Please enter a valid email address (e.g., user@example.com)');
assert.strictEqual(validateEmail('reviewer@company.com'), undefined);
assert.strictEqual(validateEmail('engineer.dev@talentintel.ai'), undefined);

// Password
assert.strictEqual(validatePassword(''), 'Password is required');
assert.strictEqual(validatePassword('short'), 'Password must be at least 8 characters long');
assert.strictEqual(validatePassword('1234567'), 'Password must be at least 8 characters long');
assert.strictEqual(validatePassword('12345678'), undefined);
assert.strictEqual(validatePassword('SecurePassword2026!'), undefined);

// Confirm Password
assert.strictEqual(validateConfirmPassword('secret1234', ''), 'Please confirm your password');
assert.strictEqual(validateConfirmPassword('secret1234', 'different1234'), 'Passwords do not match');
assert.strictEqual(validateConfirmPassword('secret1234', 'secret1234'), undefined);

// Terms
assert.strictEqual(validateTerms(false), 'You must accept the terms to continue');
assert.strictEqual(validateTerms(true), undefined);

// Password Strength
assert.strictEqual(getPasswordStrength('').label, 'Empty');
assert.strictEqual(getPasswordStrength('abc').label, 'Weak');
assert.strictEqual(getPasswordStrength('abcdefgh1').label, 'Fair');
assert.strictEqual(getPasswordStrength('Abcdefgh1').label, 'Good');
assert.strictEqual(getPasswordStrength('Abcdefgh1!@#').label, 'Strong');

console.log('  ✔ Name, email, password, confirm password, terms, and strength validators pass all checks');

// =========================================================================
// 2. apiRequest & Error Mapping Tests with Stubbed Fetch
// =========================================================================
console.log('\n▶ [2/4] Testing apiRequest Error Normalization & HTTP Dispatch');

const originalFetch = globalThis.fetch;

async function runApiTests() {
  // Test 200 OK
  globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
    return new Response(JSON.stringify({ success: true, url: String(url), method: init?.method || 'GET' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const successRes = await apiRequest<{ success: boolean; url: string; method: string }>('/test-endpoint');
  assert.strictEqual(successRes.success, true);
  assert.strictEqual(successRes.url, `${API_BASE_URL}/test-endpoint`);
  assert.strictEqual(successRes.method, 'GET');
  console.log('  ✔ apiRequest successfully dispatches GET requests and parses JSON');

  // Test 204 No Content
  globalThis.fetch = async () => {
    return new Response(null, { status: 204 });
  };
  const emptyRes = await apiRequest<object>('/no-content');
  assert.deepStrictEqual(emptyRes, {});
  console.log('  ✔ apiRequest handles 204 No Content gracefully');

  // Test 401 Unauthorized mapping
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: 'Invalid credentials' }), {
      status: 401,
      statusText: 'Unauthorized',
      headers: { 'Content-Type': 'application/json' },
    });
  };
  await assert.rejects(
    async () => {
      await apiRequest('/protected');
    },
    (err: unknown) => {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 401);
      assert.strictEqual(err.detail, 'Invalid credentials');
      assert.strictEqual(err.message.includes('401 Unauthorized'), true);
      return true;
    }
  );
  console.log('  ✔ apiRequest maps 401 Unauthorized to descriptive ApiError');

  // Test 404 Not Found mapping
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: 'Conversation not found' }), {
      status: 404,
      statusText: 'Not Found',
      headers: { 'Content-Type': 'application/json' },
    });
  };
  await assert.rejects(
    async () => {
      await apiRequest('/conversations/9999');
    },
    (err: unknown) => {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 404);
      assert.strictEqual(err.detail, 'Conversation not found');
      assert.strictEqual(err.message.includes('404 Not Found'), true);
      return true;
    }
  );
  console.log('  ✔ apiRequest maps 404 Not Found correctly');

  // Test 422 Unprocessable Entity mapping
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: 'Missing required field: sender_role' }), {
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: { 'Content-Type': 'application/json' },
    });
  };
  await assert.rejects(
    async () => {
      await apiRequest('/messages', { method: 'POST', body: '{}' });
    },
    (err: unknown) => {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 422);
      assert.strictEqual(err.detail, 'Missing required field: sender_role');
      return true;
    }
  );
  console.log('  ✔ apiRequest maps 422 Unprocessable Entity with FastAPI detail');

  // Test 500 Internal Server Error
  globalThis.fetch = async () => {
    return new Response('Database connection failed', {
      status: 500,
      statusText: 'Internal Server Error',
    });
  };
  await assert.rejects(
    async () => {
      await apiRequest('/crash');
    },
    (err: unknown) => {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 500);
      assert.strictEqual(err.message.includes('Server error (500)'), true);
      return true;
    }
  );
  console.log('  ✔ apiRequest maps 500 Internal Server Error correctly');

  // Test Network Error (fetch throws)
  globalThis.fetch = async () => {
    throw new Error('fetch failed: connect ECONNREFUSED 127.0.0.1:8010');
  };
  await assert.rejects(
    async () => {
      await apiRequest('/offline');
    },
    (err: unknown) => {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 0);
      assert.strictEqual(err.isNetworkError, true);
      assert.strictEqual(err.statusText, 'Connection Refused');
      return true;
    }
  );
  console.log('  ✔ apiRequest handles network disconnection with isNetworkError: true');
}

// =========================================================================
// 3. ChatService REST Endpoints & Client-Only Simulation Verification
// =========================================================================
async function runChatServiceTests() {
  console.log('\n▶ [3/4] Testing ChatService REST Operations & Non-Persistence of Simulations');

  let recordedCalls: { url: string; method: string; body?: string }[] = [];

  // Reset call log and mock backend responses
  recordedCalls = [];
  globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
    const urlStr = String(url);
    const method = init?.method || 'GET';
    const body = init?.body ? String(init.body) : undefined;
    recordedCalls.push({ url: urlStr, method, body });

    // Mock GET /users/{id}/conversations
    if (urlStr.includes(`/users/${DEMO_USER_ID}/conversations`) && method === 'GET') {
      const convs: BackendConversation[] = [
        { id: 42, user_id: DEMO_USER_ID, created_at: '2026-09-14T10:00:00Z', updated_at: '2026-09-14T10:05:00Z' },
        { id: 41, user_id: DEMO_USER_ID, created_at: '2026-09-14T09:00:00Z', updated_at: '2026-09-14T09:05:00Z' },
      ];
      return new Response(JSON.stringify(convs), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // Mock POST /users/{id}/conversations
    if (urlStr.includes(`/users/${DEMO_USER_ID}/conversations`) && method === 'POST') {
      const newConv: BackendConversation = {
        id: 99,
        user_id: DEMO_USER_ID,
        created_at: '2026-09-14T12:00:00Z',
        updated_at: '2026-09-14T12:00:00Z',
      };
      return new Response(JSON.stringify(newConv), { status: 201, headers: { 'Content-Type': 'application/json' } });
    }

    // Mock POST /conversations/{id}/messages
    if (urlStr.includes('/conversations/99/messages') && method === 'POST') {
      const parsed = body ? JSON.parse(body) : {};
      const savedMsg: BackendMessage = {
        id: 1001,
        conversation_id: 99,
        sender_role: parsed.sender_role,
        content: parsed.content,
        timestamp: '2026-09-14T12:01:00Z',
      };
      return new Response(JSON.stringify(savedMsg), { status: 201, headers: { 'Content-Type': 'application/json' } });
    }

    // Mock GET /conversations/{id}/messages
    if (urlStr.includes('/conversations/42/messages') && method === 'GET') {
      const msgs: BackendMessage[] = [
        { id: 1, conversation_id: 42, sender_role: 'user', content: 'Initial question', timestamp: '2026-09-14T10:00:00Z' },
      ];
      return new Response(JSON.stringify(msgs), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    return new Response(JSON.stringify({ error: 'Unhandled route in test' }), { status: 404 });
  };

  // 1. Test getSessions sends exactly ONE request (no N+1 message requests)
  const sessions = await ChatService.getSessions();
  assert.strictEqual(recordedCalls.length, 1, 'getSessions should send exactly 1 request to /users/{id}/conversations');
  assert.strictEqual(recordedCalls[0].url.endsWith(`/users/${DEMO_USER_ID}/conversations`), true);
  assert.strictEqual(sessions.length, 2);
  assert.strictEqual(sessions[0].id, '42');
  console.log('  ✔ getSessions avoids O(N) calls and retrieves conversations in a single request');

  // 2. Test createSession
  recordedCalls = [];
  const created = await ChatService.createSession(undefined, 'Evaluate Tariq');
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].method, 'POST');
  assert.strictEqual(recordedCalls[0].url.endsWith(`/users/${DEMO_USER_ID}/conversations`), true);
  assert.strictEqual(created.id, '99');
  assert.strictEqual(created.title, 'Evaluate Tariq');
  console.log('  ✔ createSession dispatches POST /users/{id}/conversations with correct payload');

  // 3. Test sendMessage:
  // - Persists user message to backend
  // - Does NOT persist assistant response to backend
  // - Labels assistant response with isSimulated: true
  // - Drops fake candidateId and matchScore
  recordedCalls = [];
  const sendResult = await ChatService.sendMessage('99', 'What is the candidate experience in FastAPI?');
  
  assert.strictEqual(
    recordedCalls.length,
    1,
    'sendMessage MUST only persist the user message to the backend (exactly 1 POST call)'
  );
  assert.strictEqual(recordedCalls[0].method, 'POST');
  assert.strictEqual(recordedCalls[0].url.endsWith('/conversations/99/messages'), true);
  
  const postedBody = JSON.parse(recordedCalls[0].body || '{}');
  assert.strictEqual(postedBody.sender_role, 'user');
  assert.strictEqual(postedBody.content, 'What is the candidate experience in FastAPI?');

  // Assistant response must be client-only and labeled
  assert.strictEqual(sendResult.assistantResponse.isSimulated, true);
  assert.strictEqual(sendResult.assistantResponse.role, 'assistant');
  assert.strictEqual(sendResult.assistantResponse.metadata?.candidateId, undefined);
  assert.strictEqual(sendResult.assistantResponse.metadata?.matchScore, undefined);
  assert.strictEqual(sendResult.assistantResponse.content.includes('Simulated Intelligence Preview'), true);
  console.log('  ✔ sendMessage saves user message to backend, keeps simulated reply client-only, and labels it');

  // 4. Test mapBackendMessage does NOT invent fake metadata
  const rawBackendMsg: BackendMessage = {
    id: 55,
    conversation_id: 99,
    sender_role: 'assistant',
    content: 'Agent answer',
    timestamp: '2026-09-14T12:05:00Z',
  };
  const mapped = mapBackendMessage(rawBackendMsg);
  assert.strictEqual(mapped.id, '55');
  assert.strictEqual(mapped.role, 'assistant');
  assert.strictEqual(mapped.metadata, undefined);
  console.log('  ✔ mapBackendMessage preserves canonical message data without invented metadata');
}

// =========================================================================
// 4. Domain Simulation Content Tests
// =========================================================================
function runDomainSimulationTests() {
  console.log('\n▶ [4/4] Testing Simulation Content & Disclaimer Presence');

  const backendPreview = generateSimulatedResponse('Tell me about FastAPI and Neo4j');
  assert.strictEqual(backendPreview.includes('Simulated Intelligence Preview'), true);
  assert.strictEqual(backendPreview.includes('Backend Architecture'), true);

  const candidatePreview = generateSimulatedResponse('Compare top candidate benchmarks');
  assert.strictEqual(candidatePreview.includes('Simulated Intelligence Preview'), true);
  assert.strictEqual(candidatePreview.includes('Candidate Comparative Benchmark'), true);

  const genericPreview = generateSimulatedResponse('Provide a general evaluation overview');
  assert.strictEqual(genericPreview.includes('Simulated Intelligence Preview'), true);
  assert.strictEqual(genericPreview.includes('Talent Intelligence Synthesis'), true);

  console.log('  ✔ All simulated responses prominently display the simulation notice');
}

// =========================================================================
// Execute Suite
// =========================================================================
async function main() {
  try {
    await runApiTests();
    await runChatServiceTests();
    runDomainSimulationTests();
    console.log('\n✅ All Task 16 Verification Tests Passed Successfully with Zero Errors!\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

main().catch((err) => {
  console.error('\n❌ Test Suite Failed:', err);
  process.exit(1);
});
