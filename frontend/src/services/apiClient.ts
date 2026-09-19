/**
 * Unified API Client for LearnerOS Backend REST Endpoints.
 * Handles base URL configuration, error normalization, and response parsing.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

export class ApiError extends Error {
  public status: number;
  public statusText: string;
  public detail: string;
  public isNetworkError: boolean;

  constructor(
    message: string,
    status = 0,
    statusText = 'Network Error',
    detail = '',
    isNetworkError = false
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.detail = detail;
    this.isNetworkError = isNetworkError;
  }
}

/**
 * Core HTTP dispatch helper encapsulating fetch logic, headers, and error normalization.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error ? err.message : 'Failed to connect to server';
    throw new ApiError(
      `Network connection failed: Unable to reach API server at ${API_BASE_URL}. ${errorMsg}`,
      0,
      'Connection Refused',
      errorMsg,
      true
    );
  }

  // Check for HTTP errors
  if (!response.ok) {
    let errorDetail = '';
    try {
      const errorJson = await response.json();
      if (typeof errorJson === 'object' && errorJson !== null) {
        errorDetail =
          errorJson.detail ||
          errorJson.message ||
          JSON.stringify(errorJson);
      }
    } catch {
      // Fallback to text body if not JSON
      try {
        errorDetail = await response.text();
      } catch {
        errorDetail = response.statusText;
      }
    }

    let userFriendlyMessage = `API request failed with status ${response.status} (${response.statusText})`;
    if (response.status === 401) {
      userFriendlyMessage = 'Authentication required or token expired (401 Unauthorized)';
    } else if (response.status === 404) {
      userFriendlyMessage = `Requested resource not found (404 Not Found): ${cleanEndpoint}`;
    } else if (response.status === 409) {
      userFriendlyMessage = `Conflict (409): ${errorDetail || 'Resource conflict'}`;
    } else if (response.status === 422) {
      userFriendlyMessage = `Validation error (422 Unprocessable Entity): ${errorDetail}`;
    } else if (response.status >= 500) {
      userFriendlyMessage = `Server error (${response.status}): ${errorDetail || 'Internal server error'}`;
    }

    throw new ApiError(
      userFriendlyMessage,
      response.status,
      response.statusText,
      errorDetail,
      false
    );
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T;
  }

  try {
    return (await response.json()) as T;
  } catch (err) {
    throw new ApiError(
      'Failed to parse server response as JSON',
      response.status,
      'Invalid JSON',
      err instanceof Error ? err.message : String(err)
    );
  }
}

/**
 * Convenience wrapper that injects a Bearer Authorization header.
 * Use for all endpoints that require JWT authentication
 * (currently: GET /users/{user_id}/conversations).
 *
 * Per backend spec (Task 17), the token is sent in the HTTP header:
 *   Authorization: Bearer <access_token>
 * and never as a query parameter.
 *
 * @param endpoint   API path (e.g. '/users/1/conversations')
 * @param token      JWT access_token from AuthContext
 * @param options    Standard RequestInit options (method, body, etc.)
 */
export async function authenticatedRequest<T>(
  endpoint: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const existingHeaders = (options.headers as Record<string, string>) || {};
  return apiRequest<T>(endpoint, {
    ...options,
    headers: {
      ...existingHeaders,
      Authorization: `Bearer ${token}`,
    },
  });
}
