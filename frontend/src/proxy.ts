/**
 * Next.js Edge Middleware — Route Protection (Task 21)
 *
 * Runs on the Edge runtime before page rendering to enforce authentication
 * on protected routes.
 *
 * Protected routes: '/' (chat dashboard)
 * Public  routes:   '/signin', '/signup'
 *
 * Token storage strategy:
 *   The AuthContext stores the JWT in sessionStorage / localStorage (client-side).
 *   Since middleware runs on the Edge (no DOM), we cannot read Web Storage here.
 *
 *   To bridge this gap without adding cookies to the auth flow (the backend
 *   returns only a Bearer token, not a Set-Cookie header), we use a lightweight
 *   client-set cookie named `learner_os_auth` that the sign-in page writes
 *   immediately after a successful sign-in — its sole purpose is to signal
 *   to middleware that the user is authenticated. The cookie contains a
 *   non-sensitive presence flag ("1"), NOT the actual JWT.
 *
 *   The actual JWT is always read from sessionStorage / localStorage by the
 *   AuthContext and injected into API request headers on the client.
 *
 * Behaviour:
 *   - Unauthenticated visit to '/'   → redirect to /signin
 *   - Authenticated visit to /signin → redirect to /
 *   - Authenticated visit to /signup → redirect to / (already registered)
 *
 * The cookie flag is removed by AuthContext.signOut() on the client side.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/** Cookie name used as the auth presence flag */
export const AUTH_COOKIE = 'learner_os_auth';

/** Routes that require authentication */
const PROTECTED_PATHS = ['/'];

/** Routes that redirect authenticated users away (already signed in) */
const AUTH_ONLY_PATHS = ['/signin', '/signup'];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasAuthCookie = Boolean(request.cookies.get(AUTH_COOKIE)?.value);

  // Redirect unauthenticated users away from protected routes
  if (PROTECTED_PATHS.some((p) => pathname === p) && !hasAuthCookie) {
    const signInUrl = request.nextUrl.clone();
    signInUrl.pathname = '/signin';
    return NextResponse.redirect(signInUrl);
  }

  // Redirect already-authenticated users away from auth pages
  if (AUTH_ONLY_PATHS.some((p) => pathname.startsWith(p)) && hasAuthCookie) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = '/';
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  /**
   * Apply middleware to the chat dashboard and auth pages.
   * Explicitly excludes Next.js internals, API routes, and static assets.
   */
  matcher: ['/', '/signin', '/signup'],
};
