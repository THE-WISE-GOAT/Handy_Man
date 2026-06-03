import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../../shared/styles/global.css';
import WorkerDashboard from './pages/Worker_Dashboard';

function App() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    const routes = {
      login: '/login',
      signup: '/signup',
      customer_dashboard: '/customer',
      worker_dashboard: '/worker',
      home: '/'
    };

    navigate(routes[target] || '/', { replace: Boolean(options.replace) });
  };

  return (
    <WorkerDashboard onNavigate={goTo} />
  );
}

export default App;