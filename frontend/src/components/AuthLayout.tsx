'use client';

import React from 'react';
import Link from 'next/link';
import { Bot, ArrowLeft } from 'lucide-react';

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  disclaimer?: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  title,
  subtitle,
  icon,
  children,
  disclaimer = 'Client-side standalone UI. Forms validate required formats locally without making requests to pending auth endpoints.',
}) => {
  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-blue-600/30 selection:text-blue-200">
      {/* Top Header Navigation */}
      <header className="w-full max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2.5 group transition-opacity hover:opacity-90"
        >
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <span className="font-semibold text-sm text-slate-100 tracking-tight flex items-center gap-1.5">
              LearnerOS
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-900/60 text-blue-300 border border-blue-500/30">
                Auth UI
              </span>
            </span>
            <p className="text-[11px] text-slate-400">Talent Intelligence Portal</p>
          </div>
        </Link>

        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/50"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Chat</span>
        </Link>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          {/* Card Container */}
          <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60 backdrop-blur-sm relative overflow-hidden">
            {/* Top Accent Gradient Border */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-500 to-blue-400" />

            {/* Header Content */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-400 mb-3 shadow-inner">
                {icon}
              </div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{title}</h1>
              <p className="text-xs text-slate-400 mt-1.5 max-w-xs mx-auto leading-relaxed">
                {subtitle}
              </p>
            </div>

            {/* Form & Page Specific Content */}
            {children}
          </div>

          {/* Phase 1 Standalone Disclaimer */}
          {disclaimer && (
            <div className="mt-6 text-center text-[11px] text-slate-400 max-w-sm mx-auto">
              <p>{disclaimer}</p>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-4 text-center text-xs text-slate-400">
        LearnerOS &copy; 2026 Talent Intelligence Platform
      </footer>
    </div>
  );
};
