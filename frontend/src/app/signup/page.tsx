'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Loader2,
} from 'lucide-react';
import { AuthLayout } from '../../components/AuthLayout';
import {
  validateName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
  validateTerms,
  getPasswordStrength,
} from '../../lib/validation';
import { AuthService } from '../../services/authService';
import { ApiError } from '../../services/apiClient';

interface FormErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  terms?: string;
}

export default function SignUpPage() {
  const router = useRouter();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  const strength = getPasswordStrength(password);

  const handleBlur = (field: keyof FormErrors) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    let error: string | undefined;
    if (field === 'name') error = validateName(name);
    if (field === 'email') error = validateEmail(email);
    if (field === 'password') error = validatePassword(password);
    if (field === 'confirmPassword') error = validateConfirmPassword(password, confirmPassword);
    if (field === 'terms') error = validateTerms(agreeTerms);
    setErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    // Client-side validation
    const validationErrors: FormErrors = {};
    const nameErr = validateName(name);
    const emailErr = validateEmail(email);
    const passErr = validatePassword(password);
    const confirmErr = validateConfirmPassword(password, confirmPassword);
    const termsErr = validateTerms(agreeTerms);

    if (nameErr) validationErrors.name = nameErr;
    if (emailErr) validationErrors.email = emailErr;
    if (passErr) validationErrors.password = passErr;
    if (confirmErr) validationErrors.confirmPassword = confirmErr;
    if (termsErr) validationErrors.terms = termsErr;

    setErrors(validationErrors);
    setTouched({ name: true, email: true, password: true, confirmPassword: true, terms: true });

    if (Object.keys(validationErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      // POST /auth/signup — backend creates the user and returns the user record (no JWT)
      await AuthService.signUp({ name: name.trim(), email: email.trim(), password });
      setRegistrationSuccess(true);
      // Redirect to sign-in after a short moment so the user sees the success state
      setTimeout(() => router.push('/signin'), 1500);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setApiError('This email address is already registered. Please sign in instead, or use a different email.');
        } else if (err.status === 422) {
          setApiError('Please check your input. The server reported a validation error: ' + err.detail);
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
      title="Create an Account"
      subtitle="Join the LearnerOS talent intelligence ecosystem to verify learner competency and analyze project artifacts."
      icon={<ShieldCheck className="w-6 h-6" />}
      disclaimer=""
    >
      {/* Registration Success State */}
      {registrationSuccess ? (
        <div className="mb-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <h2 className="text-xs font-semibold text-emerald-200">Account Created Successfully!</h2>
              <p className="text-[11px] text-emerald-400/90 mt-0.5 leading-relaxed">
                Your account has been registered. Redirecting you to Sign In…
              </p>
              <div className="mt-3">
                <Link
                  href="/signin"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors shadow-sm"
                >
                  <span>Go to Sign In</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* API Error Banner */}
          {apiError && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs">
                <p className="font-medium text-rose-200">Registration Failed</p>
                <p className="text-[11px] text-rose-400/90 mt-0.5">{apiError}</p>
                {apiError.includes('already registered') && (
                  <Link href="/signin" className="inline-flex items-center gap-1 mt-2 text-blue-400 hover:text-blue-300 underline underline-offset-4">
                    Sign in instead
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Sign Up Form */}
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Full Name */}
            <div>
              <label htmlFor="fullName" className="block text-xs font-medium text-slate-300 mb-1.5">
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
                    if (touched.name) setErrors((prev) => ({ ...prev, name: validateName(e.target.value) }));
                  }}
                  onBlur={() => handleBlur('name')}
                  placeholder="Sarah Connor"
                  aria-invalid={Boolean(errors.name)}
                  aria-describedby={errors.name ? 'name-error' : undefined}
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none disabled:opacity-50 ${
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
              <label htmlFor="signup-email" className="block text-xs font-medium text-slate-300 mb-1.5">
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
                    if (touched.email) setErrors((prev) => ({ ...prev, email: validateEmail(e.target.value) }));
                  }}
                  onBlur={() => handleBlur('email')}
                  placeholder="sarah@company.com"
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'signup-email-error' : undefined}
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none disabled:opacity-50 ${
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
              <label htmlFor="signup-password" className="block text-xs font-medium text-slate-300 mb-1.5">
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
                    if (touched.password) setErrors((prev) => ({ ...prev, password: validatePassword(e.target.value) }));
                    if (touched.confirmPassword && confirmPassword) {
                      setErrors((prev) => ({ ...prev, confirmPassword: validateConfirmPassword(e.target.value, confirmPassword) }));
                    }
                  }}
                  onBlur={() => handleBlur('password')}
                  placeholder="At least 8 characters"
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'signup-password-error' : undefined}
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
              {/* Password Strength Meter */}
              {password && (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>Strength: <strong className="text-slate-200">{strength.label}</strong></span>
                    <span>Min. 8 characters</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className={`h-full ${strength.color} transition-all duration-300`} style={{ width: `${strength.score}%` }} />
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

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirm-password" className="block text-xs font-medium text-slate-300 mb-1.5">
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
                      setErrors((prev) => ({ ...prev, confirmPassword: validateConfirmPassword(password, e.target.value) }));
                    }
                  }}
                  onBlur={() => handleBlur('confirmPassword')}
                  placeholder="Re-enter your password"
                  aria-invalid={Boolean(errors.confirmPassword)}
                  aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-slate-950/70 border rounded-xl text-slate-100 placeholder-slate-400 transition-colors focus:outline-none disabled:opacity-50 ${
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
                  tabIndex={-1}
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

            {/* Terms Checkbox */}
            <div className="pt-1">
              <label className="flex items-start gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => {
                    setAgreeTerms(e.target.checked);
                    if (touched.terms) setErrors((prev) => ({ ...prev, terms: validateTerms(e.target.checked) }));
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

            {/* Submit */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium text-xs sm:text-sm transition-all duration-150 shadow-md shadow-blue-950/40 cursor-pointer group"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Account…</span>
                  </>
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </>
                )}
              </button>
            </div>
          </form>
        </>
      )}

      {/* Footer Links */}
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
      </div>
    </AuthLayout>
  );
}
