import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/context/AuthContext';

export default function LogoutButton({ className = '', children = 'Logout', style }) {
  const navigate = useNavigate();
  const { logoutLocal } = useAuth();

  const handleLogout = () => {
    logoutLocal();
    navigate('/login', { replace: true });
  };

  return (
    <button type="button" className={className} style={style} onClick={handleLogout}>
      {children}
    </button>
  );
}
