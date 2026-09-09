'use client';

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Message, Session } from '../types/chat';
import { MessageItem } from './MessageItem';
import {
  Send,
  Menu,
  Sparkles,
  Bot,
  
  Shield,
  Lightbulb,
  ArrowUpRight,
  Loader2,
} from 'lucide-react';

interface ChatWindowProps {
  activeSession: Session | null;
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (prompt: string) => void;
  onToggleSidebar?: () => void;
}

const STARTER_PROMPTS = [
  {
    title: 'Evaluate Tariq Mansour',
    desc: 'Verify async Python, FastAPI, and Neo4j graph experience',
    prompt: 'Can you evaluate candidate Tariq Mansour for the Senior Backend Engineer role? Focus on his graph database and async Python experience.',
  },
  {
    title: 'Candidate Profile: Alex Chen',
    desc: 'Deep-dive into agentic LLM loops and offline regression suites',
    prompt: 'What are the key technical highlights and risk factors for Alex Chen in autonomous agent architectures?',
  },
  {
    title: 'Tech Lead Benchmark',
    desc: 'Compare candidate leadership, code review turnaround, and RFC rigor',
    prompt: 'Compare our top candidates for the Technical Lead role regarding architectural leadership and mentoring.',
  },
  {
    title: 'Batch Ingestion Verification',
    desc: 'Inspect idempotent data loading and UUIDv5 consistency',
    prompt: 'How do our candidates handle idempotent high-concurrency ingestion in Neo4j without lock contention?',
  },
];

export const ChatWindow: React.FC<ChatWindowProps> = ({
  activeSession,
  messages,
  isLoading,
  onSendMessage,
  onToggleSidebar,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Focus textarea on session change or new chat
  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeSession]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    onSendMessage(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="h-14 px-4 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md flex items-center justify-between flex-shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-900 md:hidden"
              aria-label="Toggle navigation sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-100 truncate">
              {activeSession ? activeSession.title : 'New Investigation'}
            </h2>
            <p className="text-[11px] text-slate-400 truncate flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              LearnerOS Talent Intelligence Agent
              {activeSession?.candidateTag && (
                <>
                  <span>•</span>
                  <span className="text-blue-400">{activeSession.candidateTag}</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-md bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
            <Shield className="w-3.5 h-3.5 text-blue-400" />
            <span>Verified Evidence</span>
          </div>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <main className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6 custom-scrollbar">
        {messages.length === 0 ? (
          /* Empty / New Chat State */
          <div className="max-w-2xl mx-auto h-full flex flex-col justify-center items-center text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white mb-4 shadow-lg shadow-blue-500/20">
              <Sparkles className="w-6 h-6" />
            </div>

            <h3 className="text-xl font-semibold text-slate-100 mb-2">
              Employer Talent Intelligence
            </h3>
            <p className="text-sm text-slate-400 max-w-md mb-8 leading-relaxed">
              Investigate candidate skills, cross-reference verified project evidence, and benchmark
              architectural competency backed by learner memory cards.
            </p>

            {/* Suggested Starter Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
              {STARTER_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(item.prompt)}
                  className="p-3.5 rounded-xl bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-blue-500/40 text-slate-200 transition-all duration-150 group cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-xs text-slate-200 group-hover:text-blue-400 flex items-center gap-1.5">
                      <Lightbulb className="w-3.5 h-3.5 text-blue-400" />
                      {item.title}
                    </span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2">{item.desc}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Render Active Message Thread */
          <div className="max-w-3xl mx-auto space-y-5">
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}

            {/* Loading / Typing Indicator */}
            {isLoading && (
              <div className="flex w-full gap-3 justify-start animate-fade-in">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 mt-1 shadow-sm">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-none p-3.5 text-slate-400 text-xs flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  <span>Agent is analyzing candidate evidence & memory cards...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input Form Bar */}
      <footer className="p-4 md:p-6 border-t border-slate-800/80 bg-slate-950/90 backdrop-blur-md flex-shrink-0">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex items-end bg-slate-900 border border-slate-800 focus-within:border-blue-500/80 rounded-2xl p-2 transition-colors shadow-lg shadow-black/40">
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about candidate skills, architecture reviews, or comparative benchmarks..."
              disabled={isLoading}
              className="flex-1 max-h-36 resize-none bg-transparent px-3 py-1.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none disabled:opacity-50"
              style={{ minHeight: '38px' }}
            />

            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 text-white transition-all cursor-pointer disabled:cursor-not-allowed flex-shrink-0 shadow-sm shadow-blue-600/30"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between px-2 pt-2 text-[11px] text-slate-400 select-none">
            <span>
              Press <kbd className="font-mono bg-slate-800 px-1 py-0.5 rounded text-[10px] text-slate-400">Enter ↵</kbd> to submit, <kbd className="font-mono bg-slate-800 px-1 py-0.5 rounded text-[10px] text-slate-400">Shift + Enter</kbd> for newline
            </span>
            <span className="hidden sm:inline">Mock Data Layer Active</span>
          </div>
        </form>
      </footer>
    </div>
  );
};
