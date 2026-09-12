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
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);

  // Initial load of sessions from decoupled service layer
  useEffect(() => {
    async function loadSessions() {
      try {
        const loadedSessions = await ChatService.getSessions();
        setSessions(loadedSessions);
        if (loadedSessions.length > 0) {
          setActiveSessionId(loadedSessions[0].id);
          setMessages(loadedSessions[0].messages);
        }
      } catch (err) {
        console.error('Failed to load initial mock sessions:', err);
      }
    }
    loadSessions();
  }, []);

  // Update active messages when selected session changes
  const handleSelectSession = useCallback(
    (sessionId: string) => {
      setActiveSessionId(sessionId);
      const selected = sessions.find((s) => s.id === sessionId);
      if (selected) {
        setMessages(selected.messages);
      }
    },
    [sessions]
  );

  // New Chat Flow: Clears active dialogue and readies input without touching prior sessions
  const handleNewChat = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
  }, []);

  // Message dispatch handler
  const handleSendMessage = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isLoading) return;

      setIsLoading(true);

      try {
        let currentSessionId = activeSessionId;

        // If in New Chat mode, create a new session first
        if (!currentSessionId) {
          const newSession = await ChatService.createSession(undefined, prompt);
          currentSessionId = newSession.id;
          setActiveSessionId(newSession.id);
        }

        // Optimistically render user message
        const optimisticUserMessage: Message = {
          id: `temp-${Date.now()}`,
          role: 'user',
          content: prompt.trim(),
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, optimisticUserMessage]);

        // Dispatch through decoupled ChatService layer
        const result = await ChatService.sendMessage(currentSessionId, prompt);

        // Replace/update thread with canonical messages from the service
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== optimisticUserMessage.id);
          return [...filtered, result.userMessage, result.assistantResponse];
        });

        // Sync session list without state leakage
        setSessions((prevSessions) => {
          const sessionIndex = prevSessions.findIndex((s) => s.id === result.updatedSession.id);
          if (sessionIndex >= 0) {
            const copy = [...prevSessions];
            copy[sessionIndex] = result.updatedSession;
            return copy;
          } else {
            return [result.updatedSession, ...prevSessions];
          }
        });
      } catch (err) {
        console.error('Failed to send message:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [activeSessionId, isLoading]
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
      />

      {/* Main Chat Area */}
      <ChatWindow
        activeSession={currentSession}
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setIsMobileSidebarOpen(true)}
      />
    </div>
  );
}
