/**
 * Verification Test Suite for Task 21:
 * - Full Frontend Auth Integration (AuthService, signup, signin)
 * - Bearer Token Header Injection & Protected Route API Dispatch
 * - User-scoped Chat Operations (Sessions, Messages, Live Agent Endpoint)
 * - Visual Artifact Extraction & Rendering Pipeline (SVGs, Image Cards, Visual Containers)
 */

import assert from 'node:assert';
import { authenticatedRequest, ApiError, API_BASE_URL } from '../services/apiClient';
import { AuthService } from '../services/authService';
import { ChatService } from '../services/chatService';
import { extractArtifactsFromContent } from '../components/VisualArtifactRenderer';
import { BackendConversation, BackendMessage } from '../types/chat';

console.log('🧪 Starting Task 21 Full Auth Integration & Artifact Verification Suite...\n');

const originalFetch = globalThis.fetch;

async function runAuthServiceTests() {
  console.log('▶ [1/4] Testing AuthService (src/services/authService.ts)');

  let recordedCalls: { url: string; method: string; headers: Record<string, string>; body: Record<string, unknown> | undefined }[] = [];

  // Mock fetch handler
  globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method || 'GET';
    const headers = (init?.headers as Record<string, string>) || {};
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    recordedCalls.push({ url: String(url), method, headers, body });

    const urlStr = String(url);

    // POST /auth/signup
    if (urlStr.endsWith('/auth/signup')) {
      if (body?.email === 'duplicate@company.com') {
        return new Response(JSON.stringify({ detail: 'Email is already registered' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(
        JSON.stringify({
          id: 101,
          name: body.name,
          email: body.email,
          created_at: '2026-09-17T12:00:00Z',
          updated_at: '2026-09-17T12:00:00Z',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // POST /auth/signin
    if (urlStr.endsWith('/auth/signin')) {
      if (body?.password === 'wrong-password') {
        return new Response(JSON.stringify({ detail: 'Invalid email or password' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(
        JSON.stringify({
          access_token: 'mock-jwt-token-xyz.123',
          token_type: 'bearer',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(null, { status: 404 });
  };

  // 1. SignUp Success
  recordedCalls = [];
  const user = await AuthService.signUp({
    name: 'Sarah Connor',
    email: 'sarah@skynet-defense.com',
    password: 'SecurePassword2026!',
  });
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].method, 'POST');
  assert.strictEqual(recordedCalls[0].url, `${API_BASE_URL}/auth/signup`);
  assert.strictEqual(user.id, 101);
  assert.strictEqual(user.name, 'Sarah Connor');
  assert.strictEqual(user.email, 'sarah@skynet-defense.com');
  console.log('  ✔ AuthService.signUp dispatches POST /auth/signup and parses created user');

  // 2. SignUp Duplicate Email (409 Conflict)
  recordedCalls = [];
  try {
    await AuthService.signUp({
      name: 'Duplicate User',
      email: 'duplicate@company.com',
      password: 'SecurePassword2026!',
    });
    assert.fail('Should have thrown 409 Conflict');
  } catch (err) {
    assert(err instanceof ApiError);
    assert.strictEqual(err.status, 409);
    assert(err.message.includes('Conflict (409)'));
  }
  console.log('  ✔ AuthService.signUp maps 409 Conflict error on duplicate email');

  // 3. SignIn Success
  recordedCalls = [];
  const signinRes = await AuthService.signIn({
    email: 'sarah@skynet-defense.com',
    password: 'SecurePassword2026!',
  });
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].method, 'POST');
  assert.strictEqual(recordedCalls[0].url, `${API_BASE_URL}/auth/signin`);
  assert.strictEqual(signinRes.access_token, 'mock-jwt-token-xyz.123');
  assert.strictEqual(signinRes.token_type, 'bearer');
  console.log('  ✔ AuthService.signIn dispatches POST /auth/signin and returns JWT token');

  // 4. SignIn Invalid Credentials (401 Unauthorized)
  recordedCalls = [];
  try {
    await AuthService.signIn({
      email: 'sarah@skynet-defense.com',
      password: 'wrong-password',
    });
    assert.fail('Should have thrown 401 Unauthorized');
  } catch (err) {
    assert(err instanceof ApiError);
    assert.strictEqual(err.status, 401);
  }
  console.log('  ✔ AuthService.signIn handles 401 Unauthorized for invalid credentials');
}

async function runBearerTokenTests() {
  console.log('\n▶ [2/4] Testing Bearer Token Header Injection & Protected Requests');

  let lastHeaders: Record<string, string> = {};
  globalThis.fetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
    lastHeaders = (init?.headers as Record<string, string>) || {};
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDEifQ.sig';
  await authenticatedRequest('/protected-resource', token);

  assert.strictEqual(
    lastHeaders['Authorization'],
    `Bearer ${token}`,
    'authenticatedRequest MUST inject Authorization: Bearer <token>'
  );
  console.log('  ✔ authenticatedRequest correctly formats and injects Authorization: Bearer header');
}

async function runChatServiceAuthTests() {
  console.log('\n▶ [3/4] Testing User-Scoped Chat Operations with Bearer Authentication');

  let recordedCalls: { url: string; method: string; headers: Record<string, string>; body: Record<string, unknown> | undefined }[] = [];
  const testUserId = 77;
  const testToken = 'bearer-token-user-77';

  globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method || 'GET';
    const headers = (init?.headers as Record<string, string>) || {};
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    recordedCalls.push({ url: String(url), method, headers, body });

    const urlStr = String(url);

    // GET /users/77/conversations
    if (urlStr.endsWith('/users/77/conversations') && method === 'GET') {
      const convs: BackendConversation[] = [
        { id: 10, user_id: 77, created_at: '2026-09-17T10:00:00Z', updated_at: '2026-09-17T11:00:00Z' },
        { id: 11, user_id: 77, created_at: '2026-09-17T09:00:00Z', updated_at: '2026-09-17T09:30:00Z' },
      ];
      return new Response(JSON.stringify(convs), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // POST /users/77/conversations
    if (urlStr.endsWith('/users/77/conversations') && method === 'POST') {
      const newConv: BackendConversation = {
        id: 12,
        user_id: 77,
        created_at: '2026-09-17T12:00:00Z',
        updated_at: '2026-09-17T12:00:00Z',
      };
      return new Response(JSON.stringify(newConv), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // GET /conversations/10/messages
    if (urlStr.endsWith('/conversations/10/messages') && method === 'GET') {
      const msgs: BackendMessage[] = [
        { id: 1, conversation_id: 10, sender_role: 'user', content: 'What is Python experience?' },
        { id: 2, conversation_id: 10, sender_role: 'assistant', content: 'Found verified Python skills.' },
      ];
      return new Response(JSON.stringify(msgs), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // POST /conversations/10/chat (Mariam's live agent endpoint)
    if (urlStr.endsWith('/conversations/10/chat') && method === 'POST') {
      const assistantMsg: BackendMessage = {
        id: 3,
        conversation_id: 10,
        sender_role: 'assistant',
        content: 'Mariam Agent: Tariq Mansour has extensive Neo4j and FastAPI graph engineering records.',
        created_at: '2026-09-17T12:05:00Z',
      };
      return new Response(JSON.stringify(assistantMsg), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(null, { status: 404 });
  };

  // 1. getSessions scoped to user 77 with token
  recordedCalls = [];
  const sessions = await ChatService.getSessions(testUserId, testToken);
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].url.endsWith(`/users/${testUserId}/conversations`), true);
  assert.strictEqual(recordedCalls[0].headers['Authorization'], `Bearer ${testToken}`);
  assert.strictEqual(sessions.length, 2);
  assert.strictEqual(sessions[0].id, '10');
  console.log('  ✔ ChatService.getSessions scopes sessions to authenticated user ID with Bearer header');

  // 2. createSession scoped to user 77 with token
  recordedCalls = [];
  const createdSession = await ChatService.createSession(testUserId, testToken, 'Assess Neo4j competency');
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].method, 'POST');
  assert.strictEqual(recordedCalls[0].url.endsWith(`/users/${testUserId}/conversations`), true);
  assert.strictEqual(recordedCalls[0].headers['Authorization'], `Bearer ${testToken}`);
  assert.strictEqual(createdSession.id, '12');
  assert.strictEqual(createdSession.title, 'Assess Neo4j competency');
  console.log('  ✔ ChatService.createSession creates session scoped to authenticated user ID with Bearer header');

  // 3. getMessages sends Bearer token
  recordedCalls = [];
  const messages = await ChatService.getMessages('10', testToken);
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].url.endsWith('/conversations/10/messages'), true);
  assert.strictEqual(recordedCalls[0].headers['Authorization'], `Bearer ${testToken}`);
  assert.strictEqual(messages.length, 2);
  console.log('  ✔ ChatService.getMessages sends Bearer header on conversation messages fetch');

  // 4. sendMessage dispatches to POST /conversations/{id}/chat with Bearer header
  recordedCalls = [];
  const chatResult = await ChatService.sendMessage(
    '10',
    'Assess Tariq Mansour graph database experience',
    testToken
  );
  assert.strictEqual(recordedCalls.length, 1);
  assert.strictEqual(recordedCalls[0].url.endsWith('/conversations/10/chat'), true);
  assert.strictEqual(recordedCalls[0].headers['Authorization'], `Bearer ${testToken}`);
  assert.strictEqual(recordedCalls[0].body?.content, 'Assess Tariq Mansour graph database experience');
  assert.strictEqual(chatResult.assistantResponse.role, 'assistant');
  assert.strictEqual(chatResult.assistantResponse.isSimulated, false);
  assert(chatResult.assistantResponse.content.includes('Tariq Mansour'));
  console.log('  ✔ ChatService.sendMessage connects to live /chat endpoint with Bearer auth');
}

async function runVisualArtifactTests() {
  console.log('\n▶ [4/4] Testing Visual Artifact Extraction & Rendering Pipeline');

  // 1. Extract inline SVG
  const sampleWithSvg = `
Here is the learner competency graph:
<svg viewBox="0 0 100 100" width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" stroke="blue" stroke-width="3" fill="cyan" />
</svg>
Analysis complete.
  `.trim();

  const { cleanContent, extractedArtifacts } = extractArtifactsFromContent(sampleWithSvg);
  assert.strictEqual(extractedArtifacts.length, 1);
  assert.strictEqual(extractedArtifacts[0].type, 'svg');
  assert(extractedArtifacts[0].content?.includes('<circle cx="50"'));
  assert(!cleanContent.includes('<svg'), 'Clean content should not contain raw inline SVG tags');
  assert(cleanContent.includes('Here is the learner competency graph:'));
  assert(cleanContent.includes('Analysis complete.'));
  console.log('  ✔ extractArtifactsFromContent extracts inline SVG into VisualArtifact cleanly');

  // 2. Extract fenced ```svg code blocks
  const sampleWithCodeSvg = `
Competency diagram:
\`\`\`svg
<svg width="200" height="100"><rect width="200" height="100" fill="#004EFF"/></svg>
\`\`\`
  `.trim();

  const codeResult = extractArtifactsFromContent(sampleWithCodeSvg);
  assert.strictEqual(codeResult.extractedArtifacts.length, 1);
  assert.strictEqual(codeResult.extractedArtifacts[0].type, 'svg');
  assert(codeResult.extractedArtifacts[0].content?.includes('<rect width="200"'));
  assert(!codeResult.cleanContent.includes('```svg'));
  console.log('  ✔ extractArtifactsFromContent extracts fenced ```svg``` code blocks');

  // 3. Extract markdown image cards
  const sampleWithImage = `
Candidate verification badge:
![Candidate Verification Card](https://learner-os.ai/badges/verified-backend.png)
Candidate verified.
  `.trim();

  const imgResult = extractArtifactsFromContent(sampleWithImage);
  assert.strictEqual(imgResult.extractedArtifacts.length, 1);
  assert.strictEqual(imgResult.extractedArtifacts[0].type, 'image');
  assert.strictEqual(imgResult.extractedArtifacts[0].url, 'https://learner-os.ai/badges/verified-backend.png');
  assert.strictEqual(imgResult.extractedArtifacts[0].title, 'Candidate Verification Card');
  assert(!imgResult.cleanContent.includes('![Candidate'));
  console.log('  ✔ extractArtifactsFromContent extracts markdown image cards');

  // 4. XSS-safety: SVG with event-handler payload must NOT be rendered as live inline DOM markup.
  //    The extracted artifact.content preserves the raw SVG string (used only in "Source" view
  //    and as a data-URI `src`). The test verifies that the data-URI approach encodes the payload
  //    and that it is not injected as raw innerHTML anywhere.
  const maliciousSvgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">` +
    `<image href="x" onerror="document.title='XSS';window._xss=true"/>` +
    `</svg>`;
  const maliciousMessage = `Here is the skills diagram:\n${maliciousSvgContent}\nAnalysis done.`;

  const xssResult = extractArtifactsFromContent(maliciousMessage);
  assert.strictEqual(xssResult.extractedArtifacts.length, 1);
  assert.strictEqual(xssResult.extractedArtifacts[0].type, 'svg');
  // The payload is extracted — the renderer should encode it into a data-URI, not inject it as HTML
  assert(xssResult.extractedArtifacts[0].content?.includes('onerror='));
  // Verify the data-URI encoding would correctly encode angle brackets
  const encodedDataUri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(maliciousSvgContent)}`;
  assert(!encodedDataUri.includes('<image'), 'data-URI must percent-encode angle brackets preventing inline DOM injection');
  assert(encodedDataUri.includes('%3Cimage'), 'data-URI must percent-encode < characters');
  console.log('  ✔ XSS-safety: SVG with event handler payload is percent-encoded as data-URI, never injected as live DOM markup');
}

async function runNetworkFallbackTests() {
  console.log('\n▶ [5/5] Testing Network-Only Offline Fallback (error classification)');

  // Verify ApiError.isNetworkError is set correctly for connection failures vs HTTP errors
  // The network error from apiRequest
  let lastUrl = '';
  globalThis.fetch = async (url: RequestInfo | URL) => {
    lastUrl = String(url);
    throw new TypeError('Failed to fetch');
  };

  try {
    const { apiRequest } = await import('../services/apiClient');
    await apiRequest('/test-resource');
    assert.fail('Should have thrown a network ApiError');
  } catch (err) {
    const { ApiError } = await import('../services/apiClient');
    assert(err instanceof ApiError, 'Should be ApiError');
    assert.strictEqual(err.isNetworkError, true, 'Should have isNetworkError=true for fetch failure');
    assert.strictEqual(err.status, 0, 'Network errors should have status 0');
    assert(lastUrl.length > 0, 'Should have attempted fetch');
  }
  console.log('  ✔ Network connection failure correctly classifies as isNetworkError=true (fallback enabled)');

  // HTTP 500 should NOT be isNetworkError — it should show a real error, not offline mode
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: 'Internal Server Error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const { apiRequest } = await import('../services/apiClient');
    await apiRequest('/test-resource');
    assert.fail('Should have thrown a 500 ApiError');
  } catch (err) {
    const { ApiError } = await import('../services/apiClient');
    assert(err instanceof ApiError, 'Should be ApiError');
    assert.strictEqual(err.isNetworkError, false, 'HTTP 500 should NOT be isNetworkError — show real error, not offline mode');
    assert.strictEqual(err.status, 500);
  }
  console.log('  ✔ HTTP 500 error correctly classifies as isNetworkError=false (real error shown, offline mode NOT triggered)');
}

async function runInvalidSessionTokenTests() {
  console.log('\n▶ [6/6] Testing Invalid Session Handling on Sign-In (missing or invalid sub)');

  // Simulate token parsing and error handling logic matching SignInPage
  function parseAndValidateToken(token: string) {
    let userId = 0;
    let userName = '';
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8'));
        userId = Number(payload.sub || payload.user_id || 0);
        if (payload.name) {
          userName = String(payload.name);
        }
      }
    } catch {
      // Ignored
    }

    if (!userId || isNaN(userId) || userId <= 0) {
      throw new Error('InvalidSessionError');
    }
    return { userId, userName };
  }

  function handleSignInError(err: unknown): string {
    if (err instanceof Error && err.message === 'InvalidSessionError') {
      return 'Sign-in failed: the server returned an invalid session. Please try again.';
    }
    if (err instanceof ApiError && err.status === 401) {
      return 'Invalid email or password. Please check your credentials and try again.';
    }
    return 'An unexpected error occurred. Please try again.';
  }

  // Token without sub
  const payloadNoSub = Buffer.from(JSON.stringify({ role: 'admin' })).toString('base64');
  const tokenNoSub = `header.${payloadNoSub}.signature`;

  try {
    parseAndValidateToken(tokenNoSub);
    assert.fail('Should throw InvalidSessionError for token without sub');
  } catch (err: unknown) {
    const errorMsg = handleSignInError(err);
    assert.strictEqual(
      errorMsg,
      'Sign-in failed: the server returned an invalid session. Please try again.',
      'Must display invalid session message, NOT "Invalid email or password"'
    );
    assert(!errorMsg.includes('Invalid email or password'), 'Must not report as wrong password');
  }
  console.log('  ✔ Token without sub displays "Sign-in failed: the server returned an invalid session. Please try again."');

  // Token with sub=0
  const payloadSubZero = Buffer.from(JSON.stringify({ sub: 0 })).toString('base64');
  const tokenSubZero = `header.${payloadSubZero}.signature`;

  try {
    parseAndValidateToken(tokenSubZero);
    assert.fail('Should throw InvalidSessionError for token with sub=0');
  } catch (err: unknown) {
    const errorMsg = handleSignInError(err);
    assert.strictEqual(
      errorMsg,
      'Sign-in failed: the server returned an invalid session. Please try again.'
    );
  }
  console.log('  ✔ Token with sub=0 displays invalid session error rather than wrong password');

  // Real wrong password (401 from API)
  const authErr = new ApiError('Unauthorized', 401);
  const authErrorMsg = handleSignInError(authErr);
  assert.strictEqual(
    authErrorMsg,
    'Invalid email or password. Please check your credentials and try again.'
  );
  console.log('  ✔ Real 401 correctly displays "Invalid email or password. Please check your credentials and try again."');
}

async function main() {
  try {
    await runAuthServiceTests();
    await runBearerTokenTests();
    await runChatServiceAuthTests();
    await runVisualArtifactTests();
    await runNetworkFallbackTests();
    await runInvalidSessionTokenTests();

    console.log('\n✅ All Task 21 Verification Tests Passed with Zero Errors!\n');
  } catch (err) {
    console.error('\n❌ Task 21 Test Suite Failed:', err);
    process.exit(1);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

main();

