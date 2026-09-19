'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Session, Message } from '../types/chat';
import { ChatService } from '../services/chatService';
import { Sidebar } from '../components/Sidebar';
import { ChatWindow } from '../components/ChatWindow';
import { useAuth } from '../contexts/AuthContext';
import { ApiError, API_BASE_URL } from '../services/apiClient';

export default function Home() {
  const { user, accessToken, isLoading: isAuthLoading, isAuthenticated, signOut } = useAuth();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFetchingSessions, setIsFetchingSessions] = useState<boolean>(true);
  const [isFetchingMessages, setIsFetchingMessages] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /**
   * Defensive 401 handler — clears invalid token and redirects to /signin.
   * Uses signOut() rather than router.push so the stale cookie is also cleared,
   * preventing the middleware <-> page redirect loop.
   */
  const handle401 = useCallback(() => {
    signOut();
  }, [signOut]);

  /**
   * Load conversation sessions scoped to the authenticated user.
   * Uses GET /users/{user_id}/conversations with Bearer token.
   *
   * Only falls back to offline/mock sessions on genuine network failures
   * (err.isNetworkError). HTTP error responses (403, 500, etc.) are shown
   * as real errors rather than silently entering offline mode.
   */
  const loadSessions = useCallback(async () => {
    if (!isAuthenticated || !user || !accessToken) return;

    setIsFetchingSessions(true);
    setErrorMessage(null);

    try {
      const loadedSessions = await ChatService.getSessions(user.id, accessToken);
      setSessions(loadedSessions);
      setIsLiveApi(true);

      if (loadedSessions.length > 0) {
        const firstSession = loadedSessions[0];
        setActiveSessionId(firstSession.id);
        try {
          const initialMessages = await ChatService.getMessages(firstSession.id, accessToken);
          setMessages(initialMessages);
          firstSession.messages = initialMessages;
        } catch {
          setMessages([]);
        }
      } else {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        handle401();
        return;
      }

      // Only fall back to offline mock sessions when the network is actually down.
      // For real HTTP errors (403, 500, etc.), show the actual error instead.
      if (err instanceof ApiError && err.isNetworkError) {
        console.warn('Backend not reachable (network error):', err);
        setIsLiveApi(false);
        const fallbackSessions = ChatService.getMockSessions();
        setSessions(fallbackSessions);
        if (fallbackSessions.length > 0) {
          setActiveSessionId(fallbackSessions[0].id);
          setMessages(fallbackSessions[0].messages || []);
        }
        setErrorMessage(
          `Notice: Backend REST server at ${API_BASE_URL} is currently offline. ` +
            `Showing local preview sessions. Once the backend is running, click Retry to connect.`
        );
      } else {
        console.error('Failed to load sessions:', err);
        const msg = err instanceof ApiError ? err.message : String(err);
        setErrorMessage(`Failed to load your conversations: ${msg}`);
      }
    } finally {
      setIsFetchingSessions(false);
    }
  }, [isAuthenticated, user, accessToken, handle401]);

  // Redirect unauthenticated users to /signin (client-side guard to complement proxy middleware).
  // Calls signOut() instead of router.push so any stale presence cookie is cleared first,
  // preventing an infinite redirect loop when sessionStorage is empty but the cookie is still set.
  useEffect(() => {
    if (!isAuthLoading && !isAuthenticated) {
      signOut();
    }
  }, [isAuthLoading, isAuthenticated, signOut]);

  // Load sessions after auth is confirmed — delegates to loadSessions (single code path).
  useEffect(() => {
    if (isAuthLoading || !isAuthenticated) return;

    let cancelled = false;

    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadSessions().finally(() => {
      if (cancelled) return;
    });

    return () => {
      cancelled = true;
    };
  }, [isAuthLoading, isAuthenticated, loadSessions]);

  // Update active messages when selected session changes
  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setActiveSessionId(sessionId);
      setErrorMessage(null);

      const localSelected = sessions.find((s) => s.id === sessionId);
      if (localSelected && localSelected.messages && localSelected.messages.length > 0) {
        setMessages(localSelected.messages);
      }

      if (isLiveApi) {
        setIsFetchingMessages(true);
        try {
          const freshMessages = await ChatService.getMessages(sessionId, accessToken || undefined);
          setMessages(freshMessages);
          setSessions((prev) =>
            prev.map((s) => (s.id === sessionId ? { ...s, messages: freshMessages } : s))
          );
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) {
            handle401();
            return;
          }
          console.error(`Failed to refresh messages for session #${sessionId}:`, err);
        } finally {
          setIsFetchingMessages(false);
        }
      }
    },
    [sessions, isLiveApi, accessToken, handle401]
  );

  const handleNewChat = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setErrorMessage(null);
  }, []);

  const handleSendMessage = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isLoading) return;

      setIsLoading(true);
      setErrorMessage(null);

      const tempId = `temp-${Date.now()}`;
      const optimisticUserMessage: Message = {
        id: tempId,
        role: 'user',
        content: prompt.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUserMessage]);

      try {
        let currentSessionId = activeSessionId;

        if (!currentSessionId) {
          if (isLiveApi && user) {
            const newSession = await ChatService.createSession(user.id, accessToken || undefined, prompt);
            currentSessionId = newSession.id;
            setActiveSessionId(newSession.id);
            setSessions((prev) => [newSession, ...prev]);
          } else {
            // Offline fallback session creation
            currentSessionId = `sess-${Date.now()}`;
            const fallbackSession: Session = {
              id: currentSessionId,
              title: prompt.slice(0, 36).trim() + (prompt.length > 36 ? '...' : ''),
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              preview: prompt.trim(),
              messages: [],
            };
            setActiveSessionId(currentSessionId);
            setSessions((prev) => [fallbackSession, ...prev]);
          }
        }

        let result;
        if (isLiveApi) {
          result = await ChatService.sendMessage(currentSessionId, prompt, accessToken || undefined);
        } else {
          const simulatedResponse =
            ChatService.getMockSessions()[0]?.messages[1]?.content || 'Candidate evidence verified.';
          const now = new Date().toISOString();
          result = {
            userMessage: {
              id: `msg-${Date.now()}-user`,
              role: 'user' as const,
              content: prompt.trim(),
              timestamp: now,
            },
            assistantResponse: {
              id: `msg-${Date.now()}-assistant`,
              role: 'assistant' as const,
              content: simulatedResponse,
              timestamp: now,
              isSimulated: true,
            },
            updatedSession: {
              id: currentSessionId,
              title: prompt.slice(0, 36).trim() + (prompt.length > 36 ? '...' : ''),
              createdAt: now,
              updatedAt: now,
              preview: prompt.trim(),
              messages: [],
            },
          };
        }

        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== tempId);
          return [...filtered, result.userMessage, result.assistantResponse];
        });

        setSessions((prevSessions) => {
          const sessionIndex = prevSessions.findIndex((s) => s.id === result.updatedSession.id);
          if (sessionIndex >= 0) {
            const copy = [...prevSessions];
            copy[sessionIndex] = { ...copy[sessionIndex], ...result.updatedSession };
            return copy;
          } else {
            return [result.updatedSession, ...prevSessions];
          }
        });
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 401) {
          handle401();
          return;
        }
        console.error('Failed to send message:', err);
        setErrorMessage('Failed to persist message to backend REST endpoint. Please check backend connection.');
        setMessages((prev) => prev.filter((m) => m.id !== tempId));
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, isLoading, isLiveApi, user, accessToken, handle401]
  );

  const currentSession = sessions.find((s) => s.id === activeSessionId) || null;

  // Show a loading state while auth is resolving
  if (isAuthLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Verifying session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        isLoadingSessions={isFetchingSessions}
        isLiveApi={isLiveApi}
        onRetryConnection={loadSessions}
        user={user}
        onLogout={signOut}
      />

      {/* Main Chat Area */}
      <ChatWindow
        activeSession={currentSession}
        messages={messages}
        isLoading={isLoading}
        isFetchingMessages={isFetchingMessages}
        error={errorMessage}
        onClearError={() => setErrorMessage(null)}
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setIsMobileSidebarOpen(true)}
        onRetry={loadSessions}
        user={user}
        onLogout={signOut}
      />
    </div>
  );
}
