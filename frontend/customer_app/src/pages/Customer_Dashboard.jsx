import React, { useState } from 'react';
import { useAuth } from '@shared/context/AuthContext';
import LogoutButton from '@shared/components/LogoutButton';
import JobIntakeForm from '@shared/components/JobIntakeForm';
import { apiClient, normalizeApiError } from '@shared/api/client';

const MAP_PREVIEW_URL = import.meta.env.VITE_MAP_STANDALONE_URL || 'http://localhost:5174';

const workerApplicationInitialFormState = {
  tradeType: ''
};

const tradeOptions = [
  'Plumbing', 'Electrical', 'Carpentry', 'HVAC', 'General Handyman', 'Appliance Repair'
];

/* ====== BACKEND COMPONENT LIFECYCLE: Fetch Authenticated User Session & Role Data Here ====== */
const mockSession = {
  user: {
    firstName: 'Aarav',
    lastName: 'Shrestha',
    locationLabel: '📍 Kathmandu, Nepal',
    accountType: 'Client Profile'
  },
  activeJob: {
    title: 'Emergency Pipe Repair',
    assignedWorker: 'Technician: Ram Bahadur',
    status: 'En Route',
    statusTone: 'is-warning',
    requestedAt: 'Today, 8:42 AM',
    eta: '12 min',
    pipeline: [
      { label: 'Requested', state: 'done' },
      { label: 'Assigned', state: 'done' },
      { label: 'In Progress', state: 'active' },
      { label: 'Completed', state: 'pending' }
    ]
  },
  quickActions: [
    { label: 'Book Plumber', icon: '🚰', meta: 'Leak repairs and line fixes' },
    { label: 'Book Electrician', icon: '⚡', meta: 'Wiring, outlets, and circuits' },
    { label: 'Smart Home Setup', icon: '🏠', meta: 'Automation, CCTV, and devices' },
    { label: 'Urgent Emergency Care', icon: '🚨', meta: 'Fast dispatch for critical issues' }
  ],
  completedOrders: [
    { date: '28 May 2026', serviceType: 'Bathroom Fitting', providerName: 'Suresh Tamang', cost: 'Rs. 3,200', receiptHref: '#receipt-bathroom' },
    { date: '19 May 2026', serviceType: 'AC Service', providerName: 'Milan Karki', cost: 'Rs. 2,450', receiptHref: '#receipt-ac' },
    { date: '05 May 2026', serviceType: 'Door Lock Repair', providerName: 'Pemba Gurung', cost: 'Rs. 1,100', receiptHref: '#receipt-lock' }
  ]
};

const pipelineOrder = mockSession.activeJob.pipeline;

export default function ClientDashboard({ onNavigate }) {
  const { username } = useAuth();
  const [intakeSummary, setIntakeSummary] = useState(null);
  const [intakeFeedback, setIntakeFeedback] = useState({ kind: 'idle', message: '' });
  const [showWorkerForm, setShowWorkerForm] = useState(false);
  const [workerApplication, setWorkerApplication] = useState(workerApplicationInitialFormState);
  const [workerAppFeedback, setWorkerAppFeedback] = useState({ kind: 'idle', message: '' });
  const [isWorkerSubmitting, setIsWorkerSubmitting] = useState(false);

  const handleJobIntakeSubmit = async (payload) => {
    setIntakeFeedback({ kind: 'loading', message: 'Preparing dispatch intake...' });

    try {
      await apiClient.post('/api/customer/problem-intake', payload);
      setIntakeSummary(payload);
      setIntakeFeedback({ kind: 'success', message: 'Intake captured and sent to the backend.' });
    } catch (error) {
      const normalized = normalizeApiError(error, 'Saved locally for now. The intake endpoint is not live yet.');
      setIntakeSummary(payload);
      setIntakeFeedback({ kind: 'warning', message: normalized.message });
    }
  };

  const handleTradeChange = (value) => {
    setWorkerApplication((prev) => ({ ...prev, tradeType: value }));
  };

  const handleWorkerSubmit = async (event) => {
    event.preventDefault();
    setIsWorkerSubmitting(true);
    setWorkerAppFeedback({ kind: 'idle', message: '' });

    try {
      await apiClient.post('/workers/apply', {
        tradeType: workerApplication.tradeType || null
      });
      setWorkerAppFeedback({ kind: 'success', message: 'Worker role activated! Redirecting...' });
      setTimeout(() => onNavigate?.('worker_dashboard', { replace: true }), 1500);
    } catch (error) {
      const normalized = normalizeApiError(error, 'Unable to transition to worker role.');
      setWorkerAppFeedback({ kind: 'error', message: normalized.message });
    } finally {
      setIsWorkerSubmitting(false);
    }
  };

  return (
    <div className="ind-page marketplace-dashboard">
      <main className="marketplace-shell">
        <header className="dash-card marketplace-header">
          <div className="marketplace-header__copy">
            <p className="marketplace-kicker">Client Dashboard</p>
            <h1>Welcome back, {username || `${mockSession.user.firstName} ${mockSession.user.lastName}`} 🛠️</h1>
            <div className="marketplace-header__meta">
              <span className="marketplace-pill">{mockSession.user.locationLabel}</span>
              <span className="marketplace-pill">{mockSession.user.accountType}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <a
              href={MAP_PREVIEW_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="marketplace-action"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                textDecoration: 'none',
                backgroundColor: '#eef6ff',
                color: '#0f3d73',
                border: '1px solid #c7ddff'
              }}
              aria-label="Open live worker map sandbox in a new tab"
            >
              🗺️ Live Worker Map (PostGIS Sandbox)
            </a>
            <button
              type="button"
              className="marketplace-action"
              style={{
                backgroundColor: '#fef3c7',
                color: '#92400e',
                border: '1px solid #f59e0b'
              }}
              onClick={() => setShowWorkerForm(true)}
            >
              Join Us as Worker
            </button>
            <button type="button" className="marketplace-action marketplace-action--primary">
              New Booking
            </button>
            <LogoutButton
              className="marketplace-action"
              children="Logout"
              style={{ backgroundColor: '#f8f8f8', color: '#222' }}
            />
          </div>
        </header>

        {showWorkerForm && (
          <div className="dash-card marketplace-card" style={{ marginTop: '1rem' }}>
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">Worker Application</p>
              <h2>Enter your trade specialization</h2>
            </div>

            <form onSubmit={handleWorkerSubmit} className="worker-transition-form">
              <div style={{ display: 'grid', gap: '12px', maxWidth: '400px' }}>
                <select
                  value={workerApplication.tradeType}
                  onChange={(e) => handleTradeChange(e.target.value)}
                  required
                >
                  <option value="">Select Your Trade</option>
                  {tradeOptions.map((trade) => (
                    <option key={trade} value={trade.toLowerCase()}>{trade}</option>
                  ))}
                </select>
              </div>

              {workerAppFeedback.message ? (
                <div
                  style={{
                    marginTop: '16px',
                    padding: '12px 14px',
                    borderRadius: '12px',
                    background: workerAppFeedback.kind === 'success' ? '#eafaf1' : '#fff7ed',
                    color: workerAppFeedback.kind === 'success' ? '#137333' : '#9a3412',
                  }}
                >
                  {workerAppFeedback.message}
                </div>
              ) : null}

              <div style={{ marginTop: '16px', display: 'flex', gap: '0.5rem' }}>
                <button
                  type="submit"
                  disabled={isWorkerSubmitting}
                  className="marketplace-action marketplace-action--primary"
                >
                  {isWorkerSubmitting ? 'ACTIVATING...' : 'Confirm Worker Role'}
                </button>
                <button
                  type="button"
                  className="marketplace-action"
                  onClick={() => setShowWorkerForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <section className="dash-card marketplace-hero" aria-labelledby="active-project-hub">
          <div className="marketplace-hero__panel">
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">Active Project Hub</p>
              <h2 id="active-project-hub">Live progress grid</h2>
            </div>

            <div className="marketplace-hero__job">
              <div>
                <span className="marketplace-label">Job Title</span>
                <strong>{mockSession.activeJob.title}</strong>
              </div>
              <div>
                <span className="marketplace-label">Assigned Worker</span>
                <strong>{mockSession.activeJob.assignedWorker}</strong>
              </div>
              <div className="marketplace-hero__status-row">
                <span className={`marketplace-status-pill ${mockSession.activeJob.statusTone}`}>
                  {mockSession.activeJob.status}
                </span>
                <span className="marketplace-mini-meta">Requested {mockSession.activeJob.requestedAt}</span>
                <span className="marketplace-mini-meta">ETA {mockSession.activeJob.eta}</span>
              </div>
            </div>
          </div>

          <div className="marketplace-hero__tracker" aria-label="Project pipeline tracker">
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">Pipeline</p>
              <h2>Requested to completed</h2>
            </div>

            <ol className="marketplace-pipeline">
              {pipelineOrder.map((step, index) => (
                <li key={step.label} className={`marketplace-pipeline__step ${step.state === 'active' ? 'is-active' : ''} ${step.state === 'done' ? 'is-done' : ''}`}>
                  <span className="marketplace-pipeline__badge">{index + 1}</span>
                  <div className="marketplace-pipeline__content">
                    <strong>{step.label}</strong>
                    <span>{step.state === 'active' ? 'Current live state' : step.state === 'done' ? 'Completed checkpoint' : 'Waiting in queue'}</span>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="dash-card marketplace-card" aria-labelledby="job-intake-hub">
          <div className="marketplace-section-head">
            <p className="marketplace-kicker">New Request</p>
            <h2 id="job-intake-hub">Create a problem intake</h2>
          </div>

          <p className="marketplace-muted" style={{ marginTop: 0 }}>
            Capture the issue in the same shape the AI extraction pipeline expects. The UI is ready now, and the backend can accept it later without redesign.
          </p>

          {intakeFeedback.message ? (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px 14px',
                borderRadius: '12px',
                background:
                  intakeFeedback.kind === 'success'
                    ? '#eafaf1'
                    : intakeFeedback.kind === 'warning'
                      ? '#fff7ed'
                      : '#f8fafc',
                color:
                  intakeFeedback.kind === 'success'
                    ? '#137333'
                    : intakeFeedback.kind === 'warning'
                      ? '#9a3412'
                      : '#334155',
                border: '1px solid rgba(148, 163, 184, 0.22)'
              }}
            >
              {intakeFeedback.message}
            </div>
          ) : null}

          <JobIntakeForm
            submitLabel="Submit intake"
            onSubmit={handleJobIntakeSubmit}
          />

          {intakeSummary ? (
            <div style={{ marginTop: '16px' }}>
              <h3 className="marketplace-kicker">Latest intake payload</h3>
              <pre
                style={{
                  margin: 0,
                  padding: '16px',
                  borderRadius: '14px',
                  background: '#0f172a',
                  color: '#dbeafe',
                  overflowX: 'auto',
                  fontSize: '13px',
                  lineHeight: 1.6
                }}
              >
                {JSON.stringify(intakeSummary, null, 2)}
              </pre>
            </div>
          ) : null}
        </section>

        <section className="marketplace-split-grid" aria-label="Quick actions and order history">
          <article className="dash-card marketplace-card">
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">Quick Actions</p>
              <h2>Book a common service</h2>
            </div>

            <div className="marketplace-actions-grid">
              {mockSession.quickActions.map((action) => (
                <button key={action.label} type="button" className="marketplace-action-card">
                  <span className="marketplace-action-card__icon" aria-hidden="true">{action.icon}</span>
                  <span className="marketplace-action-card__label">{action.label}</span>
                  <span className="marketplace-action-card__meta">{action.meta}</span>
                </button>
              ))}
            </div>
          </article>

          <article className="dash-card marketplace-card">
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">History</p>
              <h2>Past completed orders</h2>
            </div>

            <div className="marketplace-table-wrap">
              <table className="marketplace-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Service Type</th>
                    <th>Provider Name</th>
                    <th>Cost</th>
                    <th>Receipt</th>
                  </tr>
                </thead>
                <tbody>
                  {mockSession.completedOrders.map((order) => (
                    <tr key={`${order.date}-${order.serviceType}`}>
                      <td>{order.date}</td>
                      <td>{order.serviceType}</td>
                      <td>{order.providerName}</td>
                      <td>{order.cost}</td>
                      <td>
                        <a className="marketplace-table__link" href={order.receiptHref}>
                          Download Receipt
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}