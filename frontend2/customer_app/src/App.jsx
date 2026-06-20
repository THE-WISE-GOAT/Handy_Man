import React from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import HomePage from '@shared/components/HomePage';
import AdminDashboard from '@shared/components/AdminDashboard';
import LoginPage from '@shared/components/LoginPage';
import ProtectedRoute from '@shared/routes/ProtectedRoute';
import AnonymousRoute from '@shared/routes/AnonymousRoute';
import CustomerDashboard from './pages/Customer_Dashboard';

const WORKER_APP_URL = import.meta.env.VITE_WORKER_URL || 'http://localhost:5174';

export default function App() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    if (target === 'worker_dashboard') {
      window.location.href = WORKER_APP_URL + '/worker';
      return;
    }
    
    const routes = {
      login: '/login',
      signup: '/signup',
      customer_dashboard: '/customer',
      admin_dashboard: '/admin',
      home: '/'
    };

    navigate(routes[target] || '/', { replace: Boolean(options.replace) });
  };

  return (
    <div className="ind-app-shell">
      <Routes>
        <Route
          path="/"
          element={(
            <AnonymousRoute>
              <HomePage onNavigate={goTo} />
            </AnonymousRoute>
          )}
        />

        <Route
          path="/login"
          element={(
            <AnonymousRoute>
              <LoginPage initialMode="login" onNavigate={goTo} />
            </AnonymousRoute>
          )}
        />

        <Route
          path="/signup"
          element={(
            <AnonymousRoute>
              <LoginPage initialMode="signup" onNavigate={goTo} />
            </AnonymousRoute>
          )}
        />

        <Route
          path="/customer"
          element={(
            <ProtectedRoute>
              <CustomerDashboard onNavigate={goTo} />
            </ProtectedRoute>
          )}
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}