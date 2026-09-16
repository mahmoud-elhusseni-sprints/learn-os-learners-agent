/**
 * Client-Side Validation Rules for LearnerOS Auth Forms.
 * Centralized module shared across Sign In, Sign Up, and test suites.
 */

export interface PasswordStrength {
  label: 'Empty' | 'Weak' | 'Fair' | 'Good' | 'Strong';
  score: number;
  color: string;
}

export function validateName(value: string | undefined | null): string | undefined {
  if (!value || !value.trim()) {
    return 'Full name is required';
  }
  if (value.trim().length < 2) {
    return 'Name must be at least 2 characters long';
  }
  return undefined;
}

export function validateEmail(value: string | undefined | null): string | undefined {
  if (!value || !value.trim()) {
    return 'Email address is required';
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(value.trim())) {
    return 'Please enter a valid email address (e.g., user@example.com)';
  }
  return undefined;
}

export function validatePassword(value: string | undefined | null): string | undefined {
  if (!value) {
    return 'Password is required';
  }
  if (value.length < 8) {
    return 'Password must be at least 8 characters long';
  }
  return undefined;
}

export function validateConfirmPassword(
  password: string,
  confirmPassword: string | undefined | null
): string | undefined {
  if (!confirmPassword) {
    return 'Please confirm your password';
  }
  if (confirmPassword !== password) {
    return 'Passwords do not match';
  }
  return undefined;
}

export function validateTerms(value: boolean | undefined | null): string | undefined {
  if (!value) {
    return 'You must accept the terms to continue';
  }
  return undefined;
}

export function getPasswordStrength(pass: string): PasswordStrength {
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
}
