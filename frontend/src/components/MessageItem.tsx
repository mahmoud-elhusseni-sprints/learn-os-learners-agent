'use client';

import React, { useState } from 'react';
import { Message } from '../types/chat';
import { User, Sparkles, Copy, Check, ShieldCheck, Tag } from 'lucide-react';

interface MessageItemProps {
  message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
    }
  };

  const formattedTime = (() => {
    try {
      const d = new Date(message.timestamp);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  })();

  // Format assistant content with basic markdown support (headers, lists, bold, inline code, tables)
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    return (
      <div className="space-y-2 text-sm leading-relaxed">
        {lines.map((line, idx) => {
          const trimmed = line.trim();

          // Markdown headers
          if (trimmed.startsWith('### ')) {
            return (
              <h3 key={idx} className="text-base font-semibold text-slate-100 mt-3 mb-1.5 flex items-center gap-2">
                <span className="w-1.5 h-4 rounded-full bg-blue-500 inline-block"></span>
                {trimmed.replace('### ', '')}
              </h3>
            );
          }
          if (trimmed.startsWith('#### ')) {
            return (
              <h4 key={idx} className="text-sm font-semibold text-slate-200 mt-2 mb-1">
                {trimmed.replace('#### ', '')}
              </h4>
            );
          }

          // Markdown lists
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            const listText = trimmed.replace(/^[-*]\s+/, '');
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-blue-400 mt-1 text-xs">•</span>
                <span>{renderInlineFormatting(listText)}</span>
              </div>
            );
          }

          // Numbered lists
          if (/^\d+\.\s+/.test(trimmed)) {
            const num = trimmed.match(/^(\d+)\.\s+/)?.[1];
            const listText = trimmed.replace(/^\d+\.\s+/, '');
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-blue-400 font-mono text-xs font-semibold">{num}.</span>
                <span>{renderInlineFormatting(listText)}</span>
              </div>
            );
          }

          // Markdown table divider
          if (trimmed.startsWith('| :---') || trimmed.startsWith('|---')) {
            return null;
          }

          // Markdown table row
          if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
            const cells = trimmed
              .split('|')
              .filter((_, i, arr) => i > 0 && i < arr.length - 1)
              .map((c) => c.trim());

            return (
              <div
                key={idx}
                className="grid grid-cols-2 md:grid-cols-3 gap-2 p-2 bg-slate-900/60 rounded border border-slate-800 text-xs font-mono"
              >
                {cells.map((cell, cIdx) => (
                  <div key={cIdx} className={cIdx === 0 ? 'font-semibold text-slate-200' : 'text-slate-300'}>
                    {renderInlineFormatting(cell)}
                  </div>
                ))}
              </div>
            );
          }

          // Empty line
          if (!trimmed) {
            return <div key={idx} className="h-1"></div>;
          }

          // Standard paragraph
          return <p key={idx}>{renderInlineFormatting(line)}</p>;
        })}
      </div>
    );
  };

  // Helper for inline bolding and code blocks
  const renderInlineFormatting = (text: string) => {
    // Regex splits by code blocks `...` and bold **...**
    const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700/60 text-blue-300 font-mono text-xs">
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-slate-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div
      className={`flex w-full gap-3 transition-opacity duration-200 ${
        isUser ? 'justify-end' : 'justify-start'
      }`}
    >
      {/* Assistant Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 mt-1 shadow-sm">
          <Sparkles className="w-4 h-4" />
        </div>
      )}

      {/* Message Bubble Container */}
      <div
        className={`relative group max-w-[85%] md:max-w-[78%] rounded-2xl p-4 transition-all duration-150 ${
          isUser
            ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-none shadow-md shadow-blue-950/20'
            : 'bg-slate-900 border border-slate-800/90 text-slate-200 rounded-tl-none shadow-lg shadow-black/30'
        }`}
      >
        {/* Header line for Assistant */}
        {!isUser && (
          <div className="flex items-center justify-between gap-4 pb-2 mb-2 border-b border-slate-800/80 text-xs text-slate-400">
            <div className="flex items-center gap-1.5 font-medium text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
              <span>Talent Intelligence Agent</span>
              {message.metadata?.matchScore && (
                <span className="ml-2 px-1.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 font-mono text-[10px]">
                  {message.metadata.matchScore}% Match
                </span>
              )}
            </div>

            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Message Content */}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          renderFormattedContent(message.content)
        )}

        {/* Metadata Badges if present */}
        {message.metadata?.tags && message.metadata.tags.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex flex-wrap gap-1.5 items-center">
            <Tag className="w-3 h-3 text-slate-400 mr-0.5" />
            {message.metadata.tags.map((tag, tIdx) => (
              <span
                key={tIdx}
                className="px-2 py-0.5 text-[11px] rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`mt-2 text-[10px] font-mono select-none ${
            isUser ? 'text-blue-200 text-right' : 'text-slate-400 text-right'
          }`}
        >
          {formattedTime}
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 mt-1 shadow-sm">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
