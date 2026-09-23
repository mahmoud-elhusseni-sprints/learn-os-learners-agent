'use client';

import React, { useState } from 'react';
import { VisualArtifact } from '../types/chat';
import {
  Code,
  Eye,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  FileImage,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

interface VisualArtifactRendererProps {
  artifact: VisualArtifact;
}

export const VisualArtifactRenderer: React.FC<VisualArtifactRendererProps> = ({
  artifact,
}) => {
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasImgError, setHasImgError] = useState(false);

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  // ─── 1. SVG Artifact Rendering ──────────────────────────────────────────────
  if (artifact.type === 'svg' && artifact.content) {
    return (
      <div
        className={`my-3 rounded-xl border border-slate-700/80 bg-slate-950/80 overflow-hidden shadow-lg transition-all duration-200 ${
          isExpanded ? 'w-full' : 'max-w-2xl'
        }`}
      >
        {/* Artifact Header Toolbar */}
        <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-blue-500/20 text-blue-400">
              <Layers className="w-3.5 h-3.5" />
            </span>
            <span className="font-semibold text-slate-200">
              {artifact.title || 'Visual Graphic (SVG)'}
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
              vector/svg
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {/* View Mode Toggle: Preview / Code */}
            <div className="flex items-center bg-slate-800/80 rounded-lg p-0.5 border border-slate-700/60 text-[11px]">
              <button
                onClick={() => setViewMode('preview')}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-md transition-colors ${
                  viewMode === 'preview'
                    ? 'bg-blue-600 text-white font-medium'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Visual Preview"
              >
                <Eye className="w-3 h-3" />
                <span>Preview</span>
              </button>
              <button
                onClick={() => setViewMode('code')}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-md transition-colors ${
                  viewMode === 'code'
                    ? 'bg-blue-600 text-white font-medium'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="View SVG Source"
              >
                <Code className="w-3 h-3" />
                <span>Source</span>
              </button>
            </div>

            {/* Expand / Collapse */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand width'}
            >
              {isExpanded ? (
                <Minimize2 className="w-3.5 h-3.5" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Copy SVG code */}
            <button
              onClick={() => handleCopy(artifact.content || '')}
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="Copy SVG XML"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Content Area */}
        {viewMode === 'preview' ? (
          <div className="p-4 flex flex-col items-center justify-center bg-slate-900/30 overflow-x-auto min-h-[160px]">
            {!hasImgError ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={formatSvgDataUri(artifact.content)}
                alt={artifact.title || 'Visual Graphic (SVG)'}
                className="max-w-full h-auto rounded-lg shadow-sm"
                onError={() => setHasImgError(true)}
              />
            ) : (
              <div
                className="w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:rounded-lg"
                dangerouslySetInnerHTML={{ __html: sanitizeSvg(artifact.content || '') }}
              />
            )}
            {artifact.caption && (
              <p className="mt-2 text-[11px] text-slate-400 text-center italic">
                {artifact.caption}
              </p>
            )}
          </div>
        ) : (
          <div className="p-3 bg-slate-950 font-mono text-[11px] text-blue-300/90 overflow-x-auto max-h-64 custom-scrollbar">
            <pre className="whitespace-pre-wrap">{artifact.content}</pre>
          </div>
        )}
      </div>
    );
  }

  // ─── 2. Image Card Artifact Rendering ───────────────────────────────────────
  if (artifact.type === 'image' && (artifact.url || artifact.content)) {
    const imgSrc = artifact.url || artifact.content || '';
    return (
      <div className="my-3 max-w-md rounded-xl border border-slate-800 bg-slate-900 overflow-hidden shadow-lg">
        <div className="p-3 border-b border-slate-800/80 flex items-center justify-between text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <FileImage className="w-4 h-4 text-blue-400" />
            <span className="font-semibold text-slate-200 truncate">
              {artifact.title || 'Image Attachment'}
            </span>
          </div>
          {artifact.url && (
            <a
              href={artifact.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
              title="Open full size"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
        <div className="relative bg-slate-950 p-2 flex items-center justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imgSrc}
            alt={artifact.title || 'Artifact image'}
            className="max-h-72 w-auto object-contain rounded-lg shadow-sm"
          />
        </div>
        {artifact.caption && (
          <div className="p-2.5 bg-slate-900/80 border-t border-slate-800 text-[11px] text-slate-400">
            {artifact.caption}
          </div>
        )}
      </div>
    );
  }

  // ─── 3. Visual Container Artifact (Cards, Charts, Data Containers) ─────────
  return (
    <div className="my-3 rounded-xl border border-blue-500/30 bg-slate-900/90 p-4 shadow-lg text-xs space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2 text-blue-400 font-medium">
          <Sparkles className="w-4 h-4" />
          <span className="text-slate-200 font-semibold">
            {artifact.title || 'Talent Intelligence Visual Container'}
          </span>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-blue-950 text-blue-300 border border-blue-500/30">
          Artifact
        </span>
      </div>

      {artifact.content && (
        <div className="text-slate-300 leading-relaxed whitespace-pre-wrap">
          {artifact.content}
        </div>
      )}

      {artifact.metadata && Object.keys(artifact.metadata).length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
          {Object.entries(artifact.metadata).map(([k, v]) => (
            <div
              key={k}
              className="p-2 rounded-lg bg-slate-950 border border-slate-800/80"
            >
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block truncate">
                {k.replace(/_/g, ' ')}
              </span>
              <span className="text-xs font-semibold text-slate-200 font-mono mt-0.5 block truncate">
                {String(v)}
              </span>
            </div>
          ))}
        </div>
      )}

      {artifact.caption && (
        <p className="text-[11px] text-slate-400 italic pt-1">
          {artifact.caption}
        </p>
      )}
    </div>
  );
};

/**
 * Strips active script tags, inline event handlers, and dangerous external embeds from SVG.
 */
export function sanitizeSvg(svg: string): string {
  return svg
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/on\w+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)/gi, '')
    .replace(/href\s*=\s*['"]?javascript:[^'"]*['"]?/gi, '')
    .replace(/<foreignObject\b[^<]*(?:(?!<\/foreignObject>)<[^<]*)*<\/foreignObject>/gi, '');
}

/**
 * Encodes SVG string into a safe, sandboxed data-URI.
 * Supports full Unicode (em-dashes, special symbols) via UTF-8 Base64.
 */
function formatSvgDataUri(svg?: string): string {
  if (!svg) return '';
  let cleanSvg = svg.trim();
  if (!cleanSvg.includes('xmlns=')) {
    cleanSvg = cleanSvg.replace(/<svg\b/i, '<svg xmlns="http://www.w3.org/2000/svg"');
  }

  // Use Node Buffer on server / SSR
  if (typeof Buffer !== 'undefined') {
    const base64 = Buffer.from(cleanSvg, 'utf-8').toString('base64');
    return `data:image/svg+xml;base64,${base64}`;
  }

  try {
    if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
      const base64 = window.btoa(unescape(encodeURIComponent(cleanSvg)));
      return `data:image/svg+xml;base64,${base64}`;
    }
  } catch {
    // Fallback if browser environment doesn't allow btoa
  }
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(cleanSvg)}`;
}

/**
 * Utility helper to parse embedded visual artifacts from message content strings.
 * Automatically extracts:
 * 1. Fenced code blocks containing SVGs: ```svg ... ``` or ```xml ... ``` or ``` ... ```
 * 2. Raw inline `<svg ... </svg>` blocks.
 * 3. Markdown images `![title](url)`.
 */
export function extractArtifactsFromContent(content: string): {
  cleanContent: string;
  extractedArtifacts: VisualArtifact[];
} {
  const extractedArtifacts: VisualArtifact[] = [];
  let cleanContent = content;

  // 1. Extract fenced code blocks containing SVGs
  const fencedSvgRegex = /```(?:svg|xml)?\s*(<svg[\s\S]*?<\/svg>)\s*```/gi;
  let match;
  while ((match = fencedSvgRegex.exec(content)) !== null) {
    extractedArtifacts.push({
      type: 'svg',
      title: 'Vector Diagram Artifact',
      content: match[1].trim(),
    });
  }
  cleanContent = cleanContent.replace(/```(?:svg|xml)?\s*<svg[\s\S]*?<\/svg>\s*```/gi, '');

  // 2. Extract raw inline <svg ... </svg> tags if not already extracted
  const rawSvgRegex = /(<svg\b[\s\S]*?<\/svg>)/gi;
  while ((match = rawSvgRegex.exec(cleanContent)) !== null) {
    extractedArtifacts.push({
      type: 'svg',
      title: 'Vector Diagram Artifact',
      content: match[1].trim(),
    });
  }
  cleanContent = cleanContent.replace(/<svg\b[\s\S]*?<\/svg>/gi, '');

  // 3. Extract markdown images: ![caption](url)
  const imgRegex = /!\[(.*?)\]\((.*?)\)/g;
  while ((match = imgRegex.exec(cleanContent)) !== null) {
    extractedArtifacts.push({
      type: 'image',
      title: match[1] || 'Image Artifact',
      url: match[2],
      caption: match[1],
    });
  }
  cleanContent = cleanContent.replace(/!\[(.*?)\]\((.*?)\)/g, '');

  return {
    cleanContent: cleanContent.trim(),
    extractedArtifacts,
  };
}
