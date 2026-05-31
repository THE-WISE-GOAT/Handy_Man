import React from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import HomePage from '@shared/components/HomePage';
import AdminDashboard from '@shared/components/AdminDashboard';
import LoginPage from '@shared/components/LoginPage';
import ProtectedRoute from '@shared/routes/ProtectedRoute';
import AnonymousRoute from '@shared/routes/AnonymousRoute';
import CustomerDashboard from './pages/Customer_Dashboard';
import WorkerDashboard from '../../worker_app/src/pages/Worker_Dashboard';
//ANUP GURAGAiN
export default function App() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    const routes = {
      login: '/login',
      signup: '/signup',
      customer_dashboard: '/customer',
      worker_dashboard: '/worker',
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

        <Route
          path="/worker"
          element={(
            <ProtectedRoute>
              <WorkerDashboard />
            </ProtectedRoute>
          )}
        />

        <Route
          path="/admin"
          element={(
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          )}
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}