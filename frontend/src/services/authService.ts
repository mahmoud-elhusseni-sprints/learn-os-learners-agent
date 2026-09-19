/**
 * Authentication Service — LearnerOS Task 21
 *
 * Decoupled API layer for Task 17 auth endpoints:
 *   POST /auth/signup
 *   POST /auth/signin
 *
 * This module is intentionally dependency-free from React; it can be
 * called from any context, hook, or server-side utility.
 */

import { apiRequest } from './apiClient';
import type { SignUpRequest, SignInRequest, AuthUser, SignInResponse } from '../types/auth';

export const AuthService = {
  /**
   * Register a new employer account.
   * Endpoint: POST /auth/signup
   *
   * On success the backend returns the created user (no JWT).
   * The caller should then navigate to /signin.
   *
   * Possible API errors already normalised by apiRequest:
   *   409 — Email already registered
   *   422 — Validation failure (missing / malformed fields)
   */
  async signUp(payload: SignUpRequest): Promise<AuthUser> {
    return apiRequest<AuthUser>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Authenticate an existing employer and receive a JWT.
   * Endpoint: POST /auth/signin
   *
   * The returned access_token must be stored in client state (AuthContext)
   * and sent as `Authorization: Bearer <token>` on protected requests.
   *
   * Possible API errors:
   *   401 — Invalid email or password
   */
  async signIn(payload: SignInRequest): Promise<SignInResponse> {
    return apiRequest<SignInResponse>('/auth/signin', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
