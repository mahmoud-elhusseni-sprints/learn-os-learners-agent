'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Session } from '../types/chat';
import {
  Plus,
  MessageSquare,
  Search,
  Bot,
  Calendar,
  X,
  Database,
  LogIn,
  UserPlus,
  RefreshCw,
  Server,
} from 'lucide-react';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
  isLoadingSessions?: boolean;
  isLiveApi?: boolean;
  onRetryConnection?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  isMobileOpen = false,
  onCloseMobile,
  isLoadingSessions = false,
  isLiveApi = true,
  onRetryConnection,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSessions = sessions.filter((s) => {
    const q = searchQuery.toLowerCase();
    return (
      s.title.toLowerCase().includes(q) ||
      (s.candidateTag && s.candidateTag.toLowerCase().includes(q)) ||
      (s.preview && s.preview.toLowerCase().includes(q))
    );
  });

  const formatTimestamp = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const isToday = d.toDateString() === now.toDateString();
      if (isToday) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-72 md:w-80 flex flex-col bg-slate-950 border-r border-slate-800/80 text-slate-300 transform transition-transform duration-200 ease-in-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2.5 group transition-opacity hover:opacity-90"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-semibold text-sm text-slate-100 tracking-tight flex items-center gap-1.5">
                Talent Intelligence
                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-900/60 text-blue-300 border border-blue-500/30">
                  MVP
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">Employer Candidate Agent</p>
            </div>
          </Link>

          {/* Close button for mobile */}
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-900 md:hidden cursor-pointer"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={() => {
              onNewChat();
              if (onCloseMobile) onCloseMobile();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium text-sm transition-all duration-150 shadow-md shadow-blue-950/40 cursor-pointer group"
          >
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
            <span>New Investigation</span>
          </button>
        </div>

        {/* Search / Filter bar */}
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8.5 pr-3 py-1.5 text-xs bg-slate-900/90 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500/80 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs"
              >
                &times;
              </button>
            )}
          </div>
        </div>

        {/* Session List Header */}
        <div className="px-4 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Server className="w-3 h-3 text-slate-400" />
            <span>Past Sessions</span>
          </span>
          <div className="flex items-center gap-1.5">
            {onRetryConnection && (
              <button
                onClick={onRetryConnection}
                title="Refresh sessions from REST API"
                className="p-1 hover:text-slate-200 text-slate-400 transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            )}
            <span className="font-mono text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-400">
              {filteredSessions.length}
            </span>
          </div>
        </div>

        {/* Scrollable Session List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 py-1 custom-scrollbar">
          {isLoadingSessions ? (
            /* Loading Skeleton */
            <div className="space-y-2 p-2 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/60 space-y-2"
                >
                  <div className="h-3 bg-slate-800 rounded w-3/4"></div>
                  <div className="h-2.5 bg-slate-850 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-8 px-4">
              <MessageSquare className="w-6 h-6 text-slate-700 mx-auto mb-2 opacity-60" />
              <p className="text-xs text-slate-400">No matching conversations found</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Click &quot;New Investigation&quot; to start a fresh thread.
              </p>
            </div>
          ) : (
            filteredSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              return (
                <button
                  key={session.id}
                  onClick={() => {
                    onSelectSession(session.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full text-left p-2.5 rounded-xl transition-all duration-150 cursor-pointer flex flex-col gap-1 border ${
                    isActive
                      ? 'bg-blue-950/40 border-blue-600/40 text-slate-100 shadow-xs'
                      : 'bg-transparent border-transparent hover:bg-slate-900 hover:border-slate-800/80 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 w-full">
                    <span className="font-medium text-xs truncate text-slate-200">
                      {session.title}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 flex-shrink-0 flex items-center gap-0.5">
                      <Calendar className="w-2.5 h-2.5" />
                      {formatTimestamp(session.updatedAt || session.createdAt)}
                    </span>
                  </div>

                  {session.preview && (
                    <p className="text-[11px] text-slate-400 truncate w-full font-normal">
                      {session.preview}
                    </p>
                  )}

                  {session.candidateTag && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-900 text-blue-400/90 border border-slate-800">
                        {session.candidateTag}
                      </span>
                    </div>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Navigation to Standalone Auth Pages */}
        <div className="px-3 py-2 border-t border-slate-800/60 bg-slate-950/60 flex items-center gap-1.5">
          <Link
            href="/signin"
            className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-300 hover:text-slate-100 text-xs transition-colors"
          >
            <LogIn className="w-3.5 h-3.5 text-blue-400" />
            <span>Sign In</span>
          </Link>
          <Link
            href="/signup"
            className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-300 hover:text-slate-100 text-xs transition-colors"
          >
            <UserPlus className="w-3.5 h-3.5 text-indigo-400" />
            <span>Sign Up</span>
          </Link>
        </div>

        {/* Footer info: REST API Integration Indicator */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/80 text-xs">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isLiveApi ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              ></span>
              <span>{isLiveApi ? 'REST API Connected' : 'Offline / Standalone'}</span>
            </span>
            <span className="font-mono text-[10px] text-slate-400">
              {isLiveApi ? 'Port 8010' : 'Fallback'}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 flex items-center gap-1">
            <Database className="w-3 h-3 text-slate-400" />
            Sessions & messages persisted via REST API
          </p>
        </div>
      </aside>
    </>
  );
};
