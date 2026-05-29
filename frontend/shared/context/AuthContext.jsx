import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

const AuthContext = createContext(null);
const TOKEN_KEY = 'handy_man_access_token';
const TOKEN_TYPE_KEY = 'handy_man_token_type';
const USERNAME_KEY = 'handy_man_username';

const decodeTokenPayload = (token) => {
  try {
    const payloadPart = token.split('.')[1];
    if (!payloadPart) return null;

    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = atob(normalized);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
};

const hasTokenExpired = (token) => {
  const payload = decodeTokenPayload(token);
  if (!payload || !payload.exp) return false;
  const nowInSeconds = Math.floor(Date.now() / 1000);
  return nowInSeconds >= payload.exp;
};

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState('');
  const [tokenType, setTokenType] = useState('bearer');
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const storedToken = localStorage.getItem(TOKEN_KEY) || '';
      const storedTokenType = localStorage.getItem(TOKEN_TYPE_KEY) || 'bearer';
      const storedUsername = localStorage.getItem(USERNAME_KEY) || '';

      if (storedToken && !hasTokenExpired(storedToken)) {
        setAccessToken(storedToken);
        setTokenType(storedTokenType);
        setUsername(storedUsername);
      } else {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_TYPE_KEY);
        localStorage.removeItem(USERNAME_KEY);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = ({ token, type = 'bearer', usernameValue = '' }) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TOKEN_TYPE_KEY, type);
    if (usernameValue) {
      localStorage.setItem(USERNAME_KEY, usernameValue);
      setUsername(usernameValue);
    }

    setAccessToken(token);
    setTokenType(type);
  };

  const logoutLocal = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_TYPE_KEY);
    localStorage.removeItem(USERNAME_KEY);
    setAccessToken('');
    setTokenType('bearer');
    setUsername('');
  };

  const isAuthenticated = Boolean(accessToken) && !hasTokenExpired(accessToken);

  const value = useMemo(() => ({
    accessToken,
    tokenType,
    username,
    isLoading,
    isAuthenticated,
    login,
    logoutLocal
  }), [accessToken, tokenType, username, isLoading, isAuthenticated]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
