'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { AuthLayout } from '../../components/AuthLayout';
import { validateEmail, validatePassword } from '../../lib/validation';

interface FormErrors {
  email?: string;
  password?: string;
}

export default function SignInPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [clientSuccess, setClientSuccess] = useState(false);

  const handleBlur = (field: 'email' | 'password') => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const error = field === 'email' ? validateEmail(email) : validatePassword(password);
    setErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setEmail(val);
    if (touched.email) {
      setErrors((prev) => ({ ...prev, email: validateEmail(val) }));
    }
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setPassword(val);
    if (touched.password) {
      setErrors((prev) => ({ ...prev, password: validatePassword(val) }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);

    const emailErr = validateEmail(email);
    const passErr = validatePassword(password);

    const validationErrors: FormErrors = {};
    if (emailErr) validationErrors.email = emailErr;
    if (passErr) validationErrors.password = passErr;

    setErrors(validationErrors);
    setTouched({ email: true, password: true });

    if (Object.keys(validationErrors).length === 0) {
      // Client-side validation succeeds strictly without dispatching to backend
      setClientSuccess(true);
    } else {
      setClientSuccess(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to your talent intelligence workspace to evaluate candidates and review memory cards."
      icon={<Lock className="w-6 h-6" />}
    >
      {/* Client-Side Validation Success Notice */}
      {clientSuccess ? (
        <div className="mb-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <h2 className="text-xs font-semibold text-emerald-200">
                Client-side Validation Passed!
              </h2>
              <p className="text-[11px] text-emerald-400/90 mt-0.5 leading-relaxed">
                Form is valid. As specified for Phase 1, backend auth endpoints are not invoked.
              </p>
              <div className="mt-3">
                <Link
                  href="/"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors shadow-sm"
                >
                  <span>Continue to Chat Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* General Form Error Notice */}
      {isSubmitted && Object.keys(errors).length > 0 && !clientSuccess && (
        <div className="mb-6 p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-medium text-rose-200">Please review the form errors</p>
            <p className="text-[11px] text-rose-400/90 mt-0.5">
              Ensure all required fields are filled correctly before proceeding.
            </p>
          </div>
        </div>
      )}

      {/* Sign In Form */}
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-xs font-medium text-slate-300 mb-1.5">
            Work Email <span className="text-rose-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Mail className="w-4 h-4" />
            </div>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={handleEmailChange}
              onBlur={() => handleBlur('email')}
              placeholder="reviewer@company.com"
              aria-invalid={Boolean(errors.email)}
              aria-describedby={errors.email ? 'email-error' : undefined}
              className={`w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none ${
                errors.email
                  ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/50'
                  : touched.email && !errors.email
                  ? 'border-emerald-500/60 focus:border-emerald-500'
                  : 'border-slate-800 focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50'
              }`}
            />
            {touched.email && !errors.email && (
              <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            )}
          </div>
          {errors.email && (
            <p
              id="email-error"
              className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1"
            >
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              <span>{errors.email}</span>
            </p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="password" className="block text-xs font-medium text-slate-300">
              Password <span className="text-rose-400">*</span>
            </label>
            <span className="text-[11px] text-slate-400 cursor-not-allowed">
              Forgot password?
            </span>
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={handlePasswordChange}
              onBlur={() => handleBlur('password')}
              placeholder="Enter at least 8 characters"
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? 'password-error' : undefined}
              className={`w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none ${
                errors.password
                  ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/50'
                  : touched.password && !errors.password
                  ? 'border-emerald-500/60 focus:border-emerald-500'
                  : 'border-slate-800 focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && (
            <p
              id="password-error"
              className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1"
            >
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              <span>{errors.password}</span>
            </p>
          )}
        </div>

        {/* Remember Me Checkbox */}
        <div className="flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-blue-600 focus:ring-blue-500/40 focus:ring-offset-0 focus:ring-1 accent-blue-600 cursor-pointer"
            />
            <span className="text-xs text-slate-400 hover:text-slate-300">
              Keep me signed in
            </span>
          </label>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium text-xs sm:text-sm transition-all duration-150 shadow-md shadow-blue-950/40 cursor-pointer group"
          >
            <span>Sign In to Workspace</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </form>

      {/* Links Section */}
      <div className="mt-5 pt-5 border-t border-slate-800/80 text-center">
        <p className="text-xs text-slate-400">
          Don&apos;t have an account yet?{' '}
          <Link
            href="/signup"
            className="font-medium text-blue-400 hover:text-blue-300 underline underline-offset-4 transition-colors"
          >
            Create an account
          </Link>
        </p>

        <div className="mt-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Explore chat workspace directly &rarr;</span>
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}
