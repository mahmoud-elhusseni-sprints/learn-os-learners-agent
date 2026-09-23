'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { AuthLayout } from '../../components/AuthLayout';
import { validateEmail, validatePassword } from '../../lib/validation';
import { AuthService } from '../../services/authService';
import { useAuth } from '../../contexts/AuthContext';
import { ApiError } from '../../services/apiClient';

interface FormErrors {
  email?: string;
  password?: string;
}

export default function SignInPage() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    // Client-side validation
    const emailErr = validateEmail(email);
    const passErr = validatePassword(password);
    const validationErrors: FormErrors = {};
    if (emailErr) validationErrors.email = emailErr;
    if (passErr) validationErrors.password = passErr;

    setErrors(validationErrors);
    setTouched({ email: true, password: true });

    if (Object.keys(validationErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      // POST /auth/signin → { access_token, token_type }
      const { access_token } = await AuthService.signIn({ email: email.trim(), password });

      // Fetch the authenticated user's profile to get their ID
      // We decode the numeric user_id by fetching /users after sign-in
      // The backend embeds user_id in the JWT; we can also fetch from /auth/me if available.
      // Per the API spec the simplest approach is to store the email from the form
      // and fetch the user record. We parse the JWT payload (unsigned client-side read):
      let userId = 0;
      let userName = '';
      const userEmail = email.trim();
      try {
        const parts = access_token.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
          userId = Number(payload.sub || payload.user_id || 0);
          if (payload.name) {
            userName = String(payload.name);
          }
        }
      } catch {
        // Will be rejected by the validation check below
      }

      // Treat a JWT without a usable subject user ID as a failed sign-in
      if (!userId || isNaN(userId) || userId <= 0) {
        throw new ApiError(
          'Authentication failed: Invalid token payload received from server (missing user ID).',
          401,
          'Invalid Token'
        );
      }

      // Persist token + user into AuthContext (writes storage + cookie)
      signIn(
        access_token,
        { id: userId, name: userName || userEmail, email: userEmail },
        rememberMe
      );

      // Navigate to protected chat dashboard
      router.push('/');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setApiError('Invalid email or password. Please check your credentials and try again.');
        } else if (err.isNetworkError) {
          setApiError('Unable to connect to the server. Please check your network connection and try again.');
        } else {
          setApiError(err.message);
        }
      } else {
        setApiError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to your talent intelligence workspace to evaluate candidates and review memory cards."
      icon={<Lock className="w-6 h-6" />}
      disclaimer=""
    >
      {/* API Error Banner */}
      {apiError && (
        <div className="mb-5 p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-medium text-rose-200">Sign In Failed</p>
            <p className="text-[11px] text-rose-400/90 mt-0.5">{apiError}</p>
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
              disabled={isSubmitting}
              className={`w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none disabled:opacity-50 ${
                errors.email
                  ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/50'
                  : touched.email && !errors.email
                  ? 'border-emerald-500/60 focus:border-emerald-500'
                  : 'border-slate-800 focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50'
              }`}
            />
          </div>
          {errors.email && (
            <p id="email-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
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
              disabled={isSubmitting}
              className={`w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none disabled:opacity-50 ${
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
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && (
            <p id="password-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              <span>{errors.password}</span>
            </p>
          )}
        </div>

        {/* Remember Me */}
        <div className="flex items-center pt-1">
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
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-xs sm:text-sm transition-all duration-150 shadow-md shadow-blue-950/40 cursor-pointer group"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Signing in…</span>
              </>
            ) : (
              <>
                <span>Sign In to Workspace</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Footer Links */}
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
      </div>
    </AuthLayout>
  );
}
