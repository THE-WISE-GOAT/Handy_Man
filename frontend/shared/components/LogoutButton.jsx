import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/context/AuthContext';
import { API_BASE_URL } from '@shared/config/api';

export default function LogoutButton({ className = '', children = 'Logout', style }) {
  const navigate = useNavigate();
  const { accessToken, tokenType, logoutLocal } = useAuth();

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/logout`, {
        method: 'POST',
        headers: accessToken
          ? {
              Authorization: `${tokenType} ${accessToken}`
            }
          : undefined,
        credentials: 'include'
      });
    } catch {
      // Best effort only. Local state still clears even if the network call fails.
    } finally {
      logoutLocal();
      navigate('/login', { replace: true });
    }
  };

  return (
    <button type="button" className={className} style={style} onClick={handleLogout}>
      {children}
    </button>
  );
}
