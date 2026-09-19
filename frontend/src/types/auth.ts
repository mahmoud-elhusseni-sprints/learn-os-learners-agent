/**
 * Authentication type definitions for LearnerOS frontend.
 * Mirrors backend API schemas from Task 17.
 */

// ─── Request Payloads ───────────────────────────────────────────────────────

export interface SignUpRequest {
  name: string;
  email: string;
  password: string;
}

export interface SignInRequest {
  email: string;
  password: string;
}

// ─── Response Payloads ──────────────────────────────────────────────────────

/** Returned by POST /auth/signup and GET /users/{id} */
export interface AuthUser {
  id: number;
  name: string;
  email: string;
  created_at?: string;
  updated_at?: string;
}

/** Returned by POST /auth/signin */
export interface SignInResponse {
  access_token: string;
  token_type: 'bearer';
}

// ─── Client-Side State ──────────────────────────────────────────────────────

export interface AuthState {
  /** Authenticated user or null when signed out */
  user: AuthUser | null;
  /** Raw JWT access token or null */
  accessToken: string | null;
  /** True while the initial auth check is running */
  isLoading: boolean;
  /** True when a user is fully authenticated */
  isAuthenticated: boolean;
}

export interface AuthContextValue extends AuthState {
  /** Persist token + user after successful sign-in */
  signIn: (token: string, user: AuthUser, persistent?: boolean) => void;
  /** Clear token, user state, and redirect to /signin */
  signOut: () => void;
}
