'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Bot,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react';

interface FormErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  terms?: string;
}

export default function SignUpPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [clientSuccess, setClientSuccess] = useState(false);

  // Password strength calculation
  const getPasswordStrength = (pass: string): { label: string; score: number; color: string } => {
    if (!pass) return { label: 'Empty', score: 0, color: 'bg-slate-700' };
    let score = 0;
    if (pass.length >= 8) score += 1;
    if (pass.length >= 12) score += 1;
    if (/[A-Z]/.test(pass)) score += 1;
    if (/[0-9]/.test(pass)) score += 1;
    if (/[^A-Za-z0-9]/.test(pass)) score += 1;

    if (score <= 1) return { label: 'Weak', score: 20, color: 'bg-rose-500' };
    if (score === 2) return { label: 'Fair', score: 40, color: 'bg-amber-500' };
    if (score === 3) return { label: 'Good', score: 70, color: 'bg-blue-500' };
    return { label: 'Strong', score: 100, color: 'bg-emerald-500' };
  };

  const strength = getPasswordStrength(password);

  // Field validation rules
  const validateField = (field: keyof FormErrors, value: string | boolean): string | undefined => {
    if (field === 'name') {
      if (typeof value === 'string' && !value.trim()) {
        return 'Full name is required';
      }
      if (typeof value === 'string' && value.trim().length < 2) {
        return 'Name must be at least 2 characters long';
      }
    }

    if (field === 'email') {
      if (typeof value === 'string' && !value.trim()) {
        return 'Email address is required';
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (typeof value === 'string' && !emailRegex.test(value.trim())) {
        return 'Please enter a valid email address (e.g., user@example.com)';
      }
    }

    if (field === 'password') {
      if (typeof value === 'string' && !value) {
        return 'Password is required';
      }
      if (typeof value === 'string' && value.length < 8) {
        return 'Password must be at least 8 characters long';
      }
    }

    if (field === 'confirmPassword') {
      if (typeof value === 'string' && !value) {
        return 'Please confirm your password';
      }
      if (typeof value === 'string' && value !== password) {
        return 'Passwords do not match';
      }
    }

    if (field === 'terms') {
      if (!value) {
        return 'You must accept the terms to continue';
      }
    }

    return undefined;
  };

  const handleBlur = (field: keyof FormErrors) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    let val: string | boolean = '';
    if (field === 'name') val = name;
    if (field === 'email') val = email;
    if (field === 'password') val = password;
    if (field === 'confirmPassword') val = confirmPassword;
    if (field === 'terms') val = agreeTerms;

    const error = validateField(field, val);
    setErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);

    const validationErrors: FormErrors = {};
    const nameErr = validateField('name', name);
    const emailErr = validateField('email', email);
    const passErr = validateField('password', password);
    const confirmErr = validateField('confirmPassword', confirmPassword);
    const termsErr = validateField('terms', agreeTerms);

    if (nameErr) validationErrors.name = nameErr;
    if (emailErr) validationErrors.email = emailErr;
    if (passErr) validationErrors.password = passErr;
    if (confirmErr) validationErrors.confirmPassword = confirmErr;
    if (termsErr) validationErrors.terms = termsErr;

    setErrors(validationErrors);
    setTouched({
      name: true,
      email: true,
      password: true,
      confirmPassword: true,
      terms: true,
    });

    if (Object.keys(validationErrors).length === 0) {
      // Client-side validation strictly succeeds
      // NO dispatch to backend auth endpoints per Phase 1 instructions
      setClientSuccess(true);
    } else {
      setClientSuccess(false);
    }
  };

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
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
                Create an Account
              </h1>
              <p className="text-xs text-slate-400 mt-1.5 max-w-xs mx-auto">
                Join the LearnerOS talent intelligence ecosystem to verify learner competency and analyze project artifacts.
              </p>
            </div>

            {/* Client-Side Validation Success Notice */}
            {clientSuccess ? (
              <div className="mb-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-xs font-semibold text-emerald-200">
                      Registration Validation Succeeded!
                    </h2>
                    <p className="text-[11px] text-emerald-400/90 mt-0.5 leading-relaxed">
                      All form fields passed client-side validation. Backend registration endpoints remain uncalled in Phase 1.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Link
                        href="/signin"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors shadow-sm"
                      >
                        <span>Proceed to Sign In</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                      <Link
                        href="/"
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors"
                      >
                        <span>Chat Workspace</span>
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
                  <p className="font-medium text-rose-200">Please correct the highlighted errors</p>
                  <p className="text-[11px] text-rose-400/90 mt-0.5">
                    Check that your name, email, and password meet the required constraints.
                  </p>
                </div>
              </div>
            )}

            {/* Sign Up Form */}
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {/* Full Name */}
              <div>
                <label
                  htmlFor="fullName"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Full Name <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    id="fullName"
                    name="name"
                    type="text"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (touched.name) {
                        setErrors((prev) => ({ ...prev, name: validateField('name', e.target.value) }));
                      }
                    }}
                    onBlur={() => handleBlur('name')}
                    placeholder="Sarah Connor"
                    aria-invalid={Boolean(errors.name)}
                    aria-describedby={errors.name ? 'name-error' : undefined}
                    className={`w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none ${
                      errors.name
                        ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/50'
                        : touched.name && !errors.name
                        ? 'border-emerald-500/60 focus:border-emerald-500'
                        : 'border-slate-800 focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50'
                    }`}
                  />
                  {touched.name && !errors.name && (
                    <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  )}
                </div>
                {errors.name && (
                  <p id="name-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    <span>{errors.name}</span>
                  </p>
                )}
              </div>

              {/* Email Field */}
              <div>
                <label
                  htmlFor="signup-email"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Work Email <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="signup-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (touched.email) {
                        setErrors((prev) => ({ ...prev, email: validateField('email', e.target.value) }));
                      }
                    }}
                    onBlur={() => handleBlur('email')}
                    placeholder="sarah@company.com"
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={errors.email ? 'signup-email-error' : undefined}
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
                  <p id="signup-email-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    <span>{errors.email}</span>
                  </p>
                )}
              </div>

              {/* Password Field */}
              <div>
                <label
                  htmlFor="signup-password"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Password <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="signup-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (touched.password) {
                        setErrors((prev) => ({ ...prev, password: validateField('password', e.target.value) }));
                      }
                      if (touched.confirmPassword && confirmPassword) {
                        setErrors((prev) => ({
                          ...prev,
                          confirmPassword: e.target.value !== confirmPassword ? 'Passwords do not match' : undefined,
                        }));
                      }
                    }}
                    onBlur={() => handleBlur('password')}
                    placeholder="At least 8 characters"
                    aria-invalid={Boolean(errors.password)}
                    aria-describedby={errors.password ? 'signup-password-error' : undefined}
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

                {/* Password Strength Meter */}
                {password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Strength: <strong className="text-slate-200">{strength.label}</strong></span>
                      <span>Min. 8 characters</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${strength.color} transition-all duration-300`}
                        style={{ width: `${strength.score}%` }}
                      />
                    </div>
                  </div>
                )}

                {errors.password && (
                  <p id="signup-password-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    <span>{errors.password}</span>
                  </p>
                )}
              </div>

              {/* Confirm Password Field */}
              <div>
                <label
                  htmlFor="confirm-password"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Confirm Password <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="confirm-password"
                    name="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (touched.confirmPassword) {
                        setErrors((prev) => ({
                          ...prev,
                          confirmPassword: validateField('confirmPassword', e.target.value),
                        }));
                      }
                    }}
                    onBlur={() => handleBlur('confirmPassword')}
                    placeholder="Re-enter your password"
                    aria-invalid={Boolean(errors.confirmPassword)}
                    aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
                    className={`w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none ${
                      errors.confirmPassword
                        ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/50'
                        : touched.confirmPassword && !errors.confirmPassword
                        ? 'border-emerald-500/60 focus:border-emerald-500'
                        : 'border-slate-800 focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                    aria-label={showConfirmPassword ? 'Hide confirmed password' : 'Show confirmed password'}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p id="confirm-password-error" className="text-[11px] text-rose-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    <span>{errors.confirmPassword}</span>
                  </p>
                )}
              </div>

              {/* Agree to Terms Checkbox */}
              <div className="pt-1">
                <label className="flex items-start gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => {
                      setAgreeTerms(e.target.checked);
                      if (touched.terms) {
                        setErrors((prev) => ({ ...prev, terms: validateField('terms', e.target.checked) }));
                      }
                    }}
                    onBlur={() => handleBlur('terms')}
                    className="w-4 h-4 mt-0.5 rounded bg-slate-950 border-slate-700 text-blue-600 focus:ring-blue-500/40 accent-blue-600 cursor-pointer flex-shrink-0"
                  />
                  <span className="text-xs text-slate-400 leading-tight">
                    I agree to the LearnerOS Talent Intelligence Terms of Service and Privacy Policy.
                  </span>
                </label>
                {errors.terms && (
                  <p className="text-[11px] text-rose-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    <span>{errors.terms}</span>
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium text-xs sm:text-sm transition-all duration-150 shadow-md shadow-blue-950/40 cursor-pointer group"
                >
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </form>

            {/* Links Section */}
            <div className="mt-5 pt-5 border-t border-slate-800/80 text-center">
              <p className="text-xs text-slate-400">
                Already have an account?{' '}
                <Link
                  href="/signin"
                  className="font-medium text-blue-400 hover:text-blue-300 underline underline-offset-4 transition-colors"
                >
                  Sign in here
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
          </div>

          {/* Phase 1 Disclaimer Footer */}
          <div className="mt-6 text-center text-[11px] text-slate-400 max-w-sm mx-auto">
            <p>
              Client-side standalone UI. Forms validate required formats locally without making requests to pending auth endpoints.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-4 text-center text-xs text-slate-400">
        LearnerOS &copy; 2026 Talent Intelligence Platform
      </footer>
    </div>
  );
}
