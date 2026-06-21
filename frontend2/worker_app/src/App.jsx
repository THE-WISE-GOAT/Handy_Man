import React from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/context/AuthContext';
import '../../shared/styles/global.css';
import WorkerDashboard from './pages/Worker_Dashboard';

const CUSTOMER_APP_URL = import.meta.env.VITE_CUSTOMER_URL || 'http://localhost:5173';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#f4f7f6' }}>
        <div style={{ fontFamily: 'monospace', color: '#333' }}>Checking session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function MainContent() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    if (target === 'customer_dashboard') {
      window.location.href = CUSTOMER_APP_URL + '/customer';
      return;
    }
    
    const routeMap = {
      login: '/login',
      signup: '/signup',
      worker_dashboard: '/worker',
      home: '/'
    };

    const path = routeMap[target];
    if (path) {
      navigate(path, { replace: Boolean(options.replace) });
    }
  };

  return (
    <Routes>
      <Route
        path="/worker"
        element={
          <ProtectedRoute>
            <WorkerDashboard onNavigate={goTo} />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/worker" replace />} />
      <Route path="*" element={<Navigate to="/worker" replace />} />
    </Routes>
  );
}

export default MainContent;