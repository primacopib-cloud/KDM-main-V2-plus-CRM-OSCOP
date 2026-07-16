// Shared HTTP core for all API modules

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const API_V2 = `${BACKEND_URL}/api/v2`;

// Auth lives in an httpOnly cookie; no token is ever read from localStorage.
// 'cookie-session' is a placeholder that satisfies legacy guards; the backend authenticates via cookie.
export const getSessionToken = () =>
  localStorage.getItem('user') ? 'cookie-session' : null;

export const getAuthHeaders = () => {
  const token = getSessionToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`${API}${endpoint}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Une erreur est survenue');
  }

  return data;
};

export const apiCallV2 = async (endpoint, options = {}) => {
  const response = await fetch(`${API_V2}${endpoint}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Une erreur est survenue');
  }

  return data;
};
