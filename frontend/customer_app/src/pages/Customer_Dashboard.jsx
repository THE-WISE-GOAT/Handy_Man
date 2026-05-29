import React from 'react';
import { useAuth } from '@shared/context/AuthContext';
import LogoutButton from '@shared/components/LogoutButton';

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