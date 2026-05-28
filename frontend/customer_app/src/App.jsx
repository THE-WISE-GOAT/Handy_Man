import React, { useEffect, useMemo, useState } from 'react';
import HomePage from '@shared/components/HomePage';
import AdminDashboard from '@shared/components/AdminDashboard';
import LoginPage from '@shared/components/LoginPage';
import CustomerDashboard from './pages/Customer_Dashboard';
import WorkerDashboard from '../../worker_app/src/pages/Worker_Dashboard';

export default function App() {
  const resolvePage = (hashValue) => {
    const normalizedHash = (hashValue || '').replace('#', '').trim().toLowerCase();

     /* ====== TEMP ROLE ROUTING: client/login-test -> customer_dashboard, worker/login-test -> worker_dashboard.
       Remove this switch when backend session claims are available.
    ====== */
     if (normalizedHash === 'dashboard' || normalizedHash === 'client' || normalizedHash === 'customer_dashboard') return 'customer_dashboard';
     if (normalizedHash === 'worker' || normalizedHash === 'worker_dashboard') return 'worker_dashboard';
    /* ====== END TEMP ROLE ROUTING ====== */

     if (normalizedHash === 'admin' || normalizedHash === 'admin_dashboard') return 'admin_dashboard';
    if (normalizedHash === 'login') return 'login';
    if (normalizedHash === 'signup') return 'signup';

    return 'home';
  };

  const [activePage, setActivePage] = useState(() => {
    if (typeof window === 'undefined') {
      return 'home';
    }

    return resolvePage(window.location.hash);
  });

  useEffect(() => {
    const handleHashChange = () => {
      setActivePage(resolvePage(window.location.hash));
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const targetHash = activePage === 'home' ? '' : `#${activePage}`;
    if (window.location.hash !== targetHash) {
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${targetHash}`);
    }
  }, [activePage]);

  const pageNode = useMemo(() => {
    if (activePage === 'customer_dashboard') {
      return <CustomerDashboard />;
    }

    if (activePage === 'worker_dashboard') {
      return <WorkerDashboard />;
    }

    if (activePage === 'admin_dashboard') {
      return <AdminDashboard />;
    }

    if (activePage === 'login') {
      return <LoginPage initialMode="login" onNavigate={setActivePage} />;
    }

    if (activePage === 'signup') {
      return <LoginPage initialMode="signup" onNavigate={setActivePage} />;
    }

    return <HomePage onNavigate={setActivePage} />;
  }, [activePage]);

  return (
    <div className="ind-app-shell">
      {pageNode}
    </div>
  );
}