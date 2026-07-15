import { API_BASE_URL } from '@shared/config/api';

const TOKEN_KEY = 'handy_man_access_token';
const TOKEN_TYPE_KEY = 'handy_man_token_type';

export class ApiClientError extends Error {
  constructor(message, { status = 0, errors = [], data = null, url = '' } = {}) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.errors = errors;
    this.data = data;
    this.url = url;
  }
}

const safeParse = async (response) => {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    return response.json();
  }

  const text = await response.text();
  return text ? { detail: text } : null;
};

const normalizeValidationErrors = (detail) => {
  if (!Array.isArray(detail)) {
    return [];
  }

  return detail.map((item) => {
    const field = Array.isArray(item?.loc) ? item.loc.filter(Boolean).join('.') : '';
    const prefix = field ? `${field}: ` : '';
    return `${prefix}${item?.msg || 'Validation error'}`;
  });
};

export const normalizeApiError = (error, fallbackMessage = 'Request failed.') => {
  if (error instanceof ApiClientError) {
    return {
      message: error.message || fallbackMessage,
      errors: error.errors || []
    };
  }

  if (error?.name === 'AbortError') {
    return {
      message: 'Request was cancelled.',
      errors: []
    };
  }

  return {
    message: error?.message || fallbackMessage,
    errors: []
  };
};

const buildAuthHeaders = (headers = {}, { token, tokenType } = {}) => {
  const nextHeaders = new Headers(headers);
  const storedToken = token || localStorage.getItem(TOKEN_KEY) || '';
  const storedTokenType = tokenType || localStorage.getItem(TOKEN_TYPE_KEY) || 'bearer';

  if (storedToken) {
    nextHeaders.set('Authorization', `${storedTokenType} ${storedToken}`);
  }

  return nextHeaders;
};

const request = async (path, options = {}) => {
  const {
    method = 'GET',
    headers,
    body,
    token,
    tokenType,
    skipAuth = false,
    signal,
    ...rest
  } = options;

  const nextHeaders = new Headers(headers || {});

  if (!skipAuth) {
    const authHeaders = buildAuthHeaders(nextHeaders, { token, tokenType });
    nextHeaders.set('Authorization', authHeaders.get('Authorization') || '');
    if (!nextHeaders.get('Authorization')) {
      nextHeaders.delete('Authorization');
    }
  }

  const hasBody = body !== undefined && body !== null;
  let finalBody = body;

  if (hasBody && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof URLSearchParams) && !(body instanceof Blob)) {
    if (!nextHeaders.has('Content-Type')) {
      nextHeaders.set('Content-Type', 'application/json');
    }
    finalBody = JSON.stringify(body);
  }

  try {
    console.log(`[apiClient] ${method} ${API_BASE_URL}${path}`);
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: nextHeaders,
      body: finalBody,
      signal,
      ...rest
    });

    console.log(`[apiClient] Response: ${response.status} ${response.statusText}`);

    const data = await safeParse(response);

    if (!response.ok) {
      const detail = data?.detail ?? data?.message ?? data?.error ?? data;
      const errors = Array.isArray(detail)
        ? normalizeValidationErrors(detail)
        : Array.isArray(data?.errors)
          ? data.errors.map((item) => (typeof item === 'string' ? item : item?.message || JSON.stringify(item)))
          : detail
            ? [typeof detail === 'string' ? detail : JSON.stringify(detail)]
            : [];

      const message = Array.isArray(detail)
        ? 'Validation failed.'
        : typeof detail === 'string'
          ? detail
          : data?.message || data?.error || `Request failed with status ${response.status}.`;

      throw new ApiClientError(message, {
        status: response.status,
        errors,
        data,
        url: `${API_BASE_URL}${path}`
      });
    }

    return data;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    console.error(`[apiClient] Network error for ${method} ${API_BASE_URL}${path}:`, error);

    throw new ApiClientError(
      error?.message === 'Failed to fetch'
        ? 'Network error. Please check your connection and try again.'
        : error?.message || 'Network error. Please check your connection and try again.',
      {
        status: 0,
        errors: [],
        data: null,
        url: `${API_BASE_URL}${path}`
      }
    );
  }
};

export const apiClient = {
  request,
  get: (path, options = {}) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options = {}) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options = {}) => request(path, { ...options, method: 'PUT', body }),
  patch: (path, body, options = {}) => request(path, { ...options, method: 'PATCH', body }),
  delete: (path, options = {}) => request(path, { ...options, method: 'DELETE' })
};
