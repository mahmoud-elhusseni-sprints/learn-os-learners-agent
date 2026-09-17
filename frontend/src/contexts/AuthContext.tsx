'use client';

/**
 * AuthContext — LearnerOS Task 21
 *
 * Application-wide authentication state provider.
 *
 * Responsibilities:
 *  - Persist JWT access token in sessionStorage (cleared on tab close)
 *    with an optional localStorage upgrade when "keep me signed in" is set.
 *  - Decode the stored user payload (stored alongside the token).
 *  - Expose signIn / signOut actions consumed via useAuth hook.
 *  - On mount, hydrate from storage so refreshing the page keeps the session.
 *  - Detect 401 errors thrown by any ApiError and auto-sign-out.
 *
 * Token storage strategy:
 *   sessionStorage  → default (cleared when browser tab closes)
 *   localStorage    → set when `persistent=true` passed to signIn()
 *
 * Keys:
 *   LEARNER_OS_ACCESS_TOKEN  — raw JWT string
 *   LEARNER_OS_USER          — JSON-serialised AuthUser
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';
import { useRouter } from 'next/navigation';
import type { AuthContextValue, AuthUser } from '../types/auth';

// ─── Storage keys ────────────────────────────────────────────────────────────

const TOKEN_KEY = 'LEARNER_OS_ACCESS_TOKEN';
const USER_KEY  = 'LEARNER_OS_USER';

/** Presence-flag cookie read by Edge middleware — value is non-sensitive "1" */
const AUTH_COOKIE = 'learner_os_auth';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function readStorage(): { token: string | null; user: AuthUser | null } {
  if (typeof window === 'undefined') {
    return { token: null, user: null };
  }
  // Check localStorage first (persistent sessions), then sessionStorage
  const raw =
    localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
  const userRaw =
    localStorage.getItem(USER_KEY) ?? sessionStorage.getItem(USER_KEY);

  if (!raw) return { token: null, user: null };

  let user: AuthUser | null = null;
  try {
    user = userRaw ? (JSON.parse(userRaw) as AuthUser) : null;
  } catch {
    user = null;
  }

  return { token: raw, user };
}

function writeStorage(
  token: string,
  user: AuthUser,
  persistent: boolean
): void {
  const store = persistent ? localStorage : sessionStorage;
  store.setItem(TOKEN_KEY, token);
  store.setItem(USER_KEY, JSON.stringify(user));
  // Set presence-flag cookie for Edge middleware (SameSite=Lax, no HttpOnly so JS can clear it)
  const maxAge = persistent ? 60 * 60 * 24 * 7 : ''; // 7 days or session
  document.cookie = `${AUTH_COOKIE}=1; path=/; SameSite=Lax${persistent ? `; max-age=${maxAge}` : ''}`;
}

function clearStorage(): void {
  [localStorage, sessionStorage].forEach((store) => {
    store.removeItem(TOKEN_KEY);
    store.removeItem(USER_KEY);
  });
  // Remove presence-flag cookie
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0`;
}

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const [accessToken, setAccessToken] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return readStorage().token;
  });
  const [user, setUser] = useState<AuthUser | null>(() => {
    if (typeof window === 'undefined') return null;
    return readStorage().user;
  });
  const isLoading = false;

  /**
   * Persist the JWT and user record received from POST /auth/signin.
   * @param token       Raw JWT access_token string
   * @param authUser    User object from backend
   * @param persistent  When true, use localStorage (survives tab close)
   */
  const signIn = useCallback(
    (token: string, authUser: AuthUser, persistent = false) => {
      writeStorage(token, authUser, persistent);
      setAccessToken(token);
      setUser(authUser);
    },
    []
  );

  /**
   * Clear tokens, reset state, and redirect to /signin.
   * Called on explicit logout OR when a 401 is received.
   */
  const signOut = useCallback(() => {
    clearStorage();
    setAccessToken(null);
    setUser(null);
    router.push('/signin');
  }, [router]);

  const isAuthenticated = Boolean(accessToken && user);

  const value = useMemo<AuthContextValue>(
    () => ({ user, accessToken, isLoading, isAuthenticated, signIn, signOut }),
    [user, accessToken, isLoading, isAuthenticated, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Consume the auth context anywhere within the AuthProvider tree.
 * Throws if called outside the provider boundary.
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}

export { AuthContext };
