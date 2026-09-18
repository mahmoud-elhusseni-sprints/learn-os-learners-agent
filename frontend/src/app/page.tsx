'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Session, Message } from '../types/chat';
import { ChatService } from '../services/chatService';
import { Sidebar } from '../components/Sidebar';
import { ChatWindow } from '../components/ChatWindow';

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFetchingSessions, setIsFetchingSessions] = useState<boolean>(true);
  const [isFetchingMessages, setIsFetchingMessages] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load conversation sessions from backend REST API (used for manual refresh / retry)
  const loadSessions = useCallback(async () => {
    setIsFetchingSessions(true);
    setErrorMessage(null);

    try {
      const loadedSessions = await ChatService.getSessions();
      setSessions(loadedSessions);
      setIsLiveApi(true);

      if (loadedSessions.length > 0) {
        const firstSession = loadedSessions[0];
        setActiveSessionId(firstSession.id);
        try {
          const initialMessages = await ChatService.getMessages(firstSession.id);
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
      console.warn('Backend REST endpoint not reachable or returned an error:', err);
      setIsLiveApi(false);

      const fallbackSessions = ChatService.getMockSessions();
      setSessions(fallbackSessions);

      if (fallbackSessions.length > 0) {
        setActiveSessionId(fallbackSessions[0].id);
        setMessages(fallbackSessions[0].messages || []);
      }

      setErrorMessage(
        'Notice: Backend REST server at http://localhost:8010 is currently offline. Showing local sessions. Once docker-compose or backend is running, click Retry to connect.'
      );
    } finally {
      setIsFetchingSessions(false);
    }
  }, []);

  // Initial mount load
  useEffect(() => {
    let ignore = false;
    async function fetchInitial() {
      try {
        const loadedSessions = await ChatService.getSessions();
        if (ignore) return;
        setSessions(loadedSessions);
        setIsLiveApi(true);

        if (loadedSessions.length > 0) {
          const firstSession = loadedSessions[0];
          setActiveSessionId(firstSession.id);
          try {
            const initialMessages = await ChatService.getMessages(firstSession.id);
            if (!ignore) {
              setMessages(initialMessages);
              firstSession.messages = initialMessages;
            }
          } catch {
            if (!ignore) setMessages([]);
          }
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      } catch (err: unknown) {
        if (ignore) return;
        console.warn('Backend REST endpoint not reachable or returned an error:', err);
        setIsLiveApi(false);

        const fallbackSessions = ChatService.getMockSessions();
        setSessions(fallbackSessions);

        if (fallbackSessions.length > 0) {
          setActiveSessionId(fallbackSessions[0].id);
          setMessages(fallbackSessions[0].messages || []);
        }

        setErrorMessage(
          'Notice: Backend REST server at http://localhost:8010 is currently offline. Showing local sessions. Once docker-compose or backend is running, click Retry to connect.'
        );
      } finally {
        if (!ignore) {
          setIsFetchingSessions(false);
        }
      }
    }

    fetchInitial();
    return () => {
      ignore = true;
    };
  }, []);

  // Update active messages when selected session changes
  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setActiveSessionId(sessionId);
      setErrorMessage(null);

      // Find locally first to avoid UI blanking
      const localSelected = sessions.find((s) => s.id === sessionId);
      if (localSelected && localSelected.messages && localSelected.messages.length > 0) {
        setMessages(localSelected.messages);
      }

      // If live API is connected, dynamically load fresh message history from GET /conversations/{id}/messages
      if (isLiveApi) {
        setIsFetchingMessages(true);
        try {
          const freshMessages = await ChatService.getMessages(sessionId);
          setMessages(freshMessages);

          // Sync into session state
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId ? { ...s, messages: freshMessages } : s
            )
          );
        } catch (err) {
          console.error(`Failed to refresh messages for session #${sessionId}:`, err);
        } finally {
          setIsFetchingMessages(false);
        }
      }
    },
    [sessions, isLiveApi]
  );

  // New Chat Flow: Clears active dialogue and readies input without touching prior sessions
  const handleNewChat = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setErrorMessage(null);
  }, []);

  // Message dispatch handler: Persists to backend REST endpoints
  const handleSendMessage = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isLoading) return;

      setIsLoading(true);
      setErrorMessage(null);

      // Temporary optimistic user message for instant UI responsiveness
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

        // If starting a new session or activeSessionId is null, create on backend
        if (!currentSessionId) {
          if (isLiveApi) {
            const newSession = await ChatService.createSession(undefined, prompt);
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

        // Dispatch through decoupled ChatService layer
        let result;
        if (isLiveApi) {
          result = await ChatService.sendMessage(currentSessionId, prompt);
        } else {
          // Offline fallback synthesis
          const simulatedResponse = ChatService.getMockSessions()[0]?.messages[1]?.content || 'Candidate evidence verified.';
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

        // Update message thread with canonical persisted messages
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== tempId);
          return [...filtered, result.userMessage, result.assistantResponse];
        });

        // Sync session list
        setSessions((prevSessions) => {
          const sessionIndex = prevSessions.findIndex(
            (s) => s.id === result.updatedSession.id
          );
          if (sessionIndex >= 0) {
            const copy = [...prevSessions];
            copy[sessionIndex] = {
              ...copy[sessionIndex],
              ...result.updatedSession,
            };
            return copy;
          } else {
            return [result.updatedSession, ...prevSessions];
          }
        });
      } catch (err: unknown) {
        console.error('Failed to send message:', err);
        setErrorMessage(
          'Failed to persist message to backend REST endpoint. Please check backend connection.'
        );
        // Remove the temporary message on failure
        setMessages((prev) => prev.filter((m) => m.id !== tempId));
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, isLoading, isLiveApi]
  );

  const currentSession = sessions.find((s) => s.id === activeSessionId) || null;

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
      />
    </div>
  );
}
