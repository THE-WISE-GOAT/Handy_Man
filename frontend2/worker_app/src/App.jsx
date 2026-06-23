import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import "../../shared/styles/global.css";
import WorkerDashboard from "./pages/Worker_Dashboard";

const CUSTOMER_APP_URL =
  import.meta.env.VITE_CUSTOMER_URL || "http://localhost:5173";

function MainContent() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    if (target === "customer_dashboard") {
      window.location.href = CUSTOMER_APP_URL + "/customer";
      return;
    }

    const routeMap = {
      login: "/login",
      signup: "/signup",
      worker_dashboard: "/worker",
      home: "/",
    };

    const path = routeMap[target];
    if (path) {
      navigate(path, { replace: Boolean(options.replace) });
    }
  };

  return (
    <Routes>
      <Route path="/worker" element={<WorkerDashboard onNavigate={goTo} />} />
      <Route path="/" element={<Navigate to="/worker" replace />} />
      <Route path="*" element={<Navigate to="/worker" replace />} />
    </Routes>
  );
}

export default MainContent;
