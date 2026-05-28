import React, { useState } from 'react';

/* ====== BACKEND COMPONENT LIFECYCLE: Fetch Authenticated User Session & Role Data Here ====== */
const mockSession = {
  worker: {
    fullName: 'Ram Bahadur Thapa',
    trade: 'Plumbing',
    verificationLabel: 'Verified Plumbing Specialist',
    walletBalance: 'Rs. 14,500',
    rating: '⭐ 4.9 (42 Reviews)',
    completedShifts: '18 Jobs Completed this month'
  },
  liveDispatch: {
    customerName: 'Anita Shrestha',
    distance: '1.2 km away',
    urgency: '🚨 Urgent Care',
    payoutRate: 'Rs. 2,400 payout',
    projectTitle: 'Emergency Pipe Repair',
    homeAddress: 'Maharajgunj, Kathmandu',
    scheduledAt: 'Available now',
    summary: 'Burst line isolation and pressure-safe reroute'
  },
  acceptedJob: {
    projectTitle: 'Emergency Pipe Repair',
    nextStep: 'Navigation started and customer notified.'
  },
  upcomingSchedule: [
    {
      customerName: 'Suman KC',
      homeAddress: 'Boudha, Kathmandu',
      scheduledTimestamp: 'Thu, 10:00 AM',
      projectDetails: 'Water heater inspection and valve replacement'
    },
    {
      customerName: 'Mina Rai',
      homeAddress: 'Lalitpur, Jawalakhel',
      scheduledTimestamp: 'Thu, 3:30 PM',
      projectDetails: 'Kitchen sink fitting and leak seal'
    },
    {
      customerName: 'Prakash Lama',
      homeAddress: 'Chabahil, Kathmandu',
      scheduledTimestamp: 'Fri, 9:15 AM',
      projectDetails: 'Drain inspection and pipe rerouting'
    }
  ]
};

export default function WorkerDashboard() {
  const [isOnline, setIsOnline] = useState(true);
  const [dispatchState, setDispatchState] = useState('live');

  const isDispatchLive = dispatchState === 'live';

  // Clicking this switch should immediately update the worker's visibility in the job feed,
  // which is exactly where the backend availability flag will later be synchronized.
  const handleAvailabilityToggle = () => {
    setIsOnline((current) => !current);
  };

  // Accepting a dispatch should promote the live job into the worker's active state,
  // clear the emergency card, and leave a durable confirmation surface for the current session.
  const handleAcceptJob = () => {
    setDispatchState('accepted');
  };

  // Declining a dispatch should remove the offer from the active queue without disturbing
  // the rest of the worker's scheduled assignments.
  const handleDeclineJob = () => {
    setDispatchState('declined');
  };

  return (
    <div className="ind-page marketplace-dashboard">
      <main className="marketplace-shell">
        <header className="dash-card marketplace-header marketplace-header--worker">
          <div className="marketplace-header__copy">
            <p className="marketplace-kicker">Worker Dashboard</p>
            <h1>
              {mockSession.worker.fullName} | Verified {mockSession.worker.trade} Specialist
            </h1>
            <div className="marketplace-header__meta">
              <span className="marketplace-pill">{mockSession.worker.verificationLabel}</span>
              <span className={`marketplace-pill ${isOnline ? 'is-online' : 'is-offline'}`}>
                {isOnline ? '[● ONLINE / RECEIVING JOBS]' : '[○ OFFLINE]'}
              </span>
            </div>
          </div>

          <button
            type="button"
            className={`marketplace-toggle ${isOnline ? 'is-online' : 'is-offline'}`}
            onClick={handleAvailabilityToggle}
          >
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </button>
        </header>

        <section className="marketplace-metrics-grid" aria-label="Worker performance metrics">
          <article className="dash-card marketplace-metric">
            <p className="marketplace-kicker">Wallet Balance</p>
            <h2>{mockSession.worker.walletBalance}</h2>
            <p className="marketplace-muted">Outstanding earnings ready for withdrawal.</p>
            <button type="button" className="marketplace-action marketplace-action--secondary">
              Withdraw Funds
            </button>
          </article>

          <article className="dash-card marketplace-metric">
            <p className="marketplace-kicker">Job Rating</p>
            <h2>{mockSession.worker.rating}</h2>
            <p className="marketplace-muted">Live feedback rolling in from verified customers.</p>
          </article>

          <article className="dash-card marketplace-metric">
            <p className="marketplace-kicker">Completed Shifts</p>
            <h2>{mockSession.worker.completedShifts}</h2>
            <p className="marketplace-muted">This month’s completed task count.</p>
          </article>
        </section>

        <section className="marketplace-split-grid marketplace-split-grid--worker" aria-label="Dispatch and schedule center">
          <article className={`dash-card marketplace-dispatch ${isDispatchLive ? 'is-hot' : ''}`}>
            <div className="marketplace-section-head marketplace-section-head--contrast">
              <p className="marketplace-kicker">Urgent Live Dispatches</p>
              <h2>High priority job alert</h2>
            </div>

            {isDispatchLive ? (
              <div className="marketplace-dispatch__body">
                <div className="marketplace-dispatch__summary">
                  <div>
                    <span className="marketplace-label">Customer</span>
                    <strong>{mockSession.liveDispatch.customerName}</strong>
                  </div>
                  <div>
                    <span className="marketplace-label">Distance</span>
                    <strong>{mockSession.liveDispatch.distance}</strong>
                  </div>
                  <div>
                    <span className="marketplace-label">Urgency</span>
                    <strong>{mockSession.liveDispatch.urgency}</strong>
                  </div>
                  <div>
                    <span className="marketplace-label">Payout</span>
                    <strong>{mockSession.liveDispatch.payoutRate}</strong>
                  </div>
                  <div>
                    <span className="marketplace-label">Project</span>
                    <strong>{mockSession.liveDispatch.projectTitle}</strong>
                  </div>
                  <div>
                    <span className="marketplace-label">Address</span>
                    <strong>{mockSession.liveDispatch.homeAddress}</strong>
                  </div>
                  <p className="marketplace-muted marketplace-muted--contrast">
                    {mockSession.liveDispatch.summary}
                  </p>
                </div>

                <div className="marketplace-dispatch__actions">
                  <button type="button" className="marketplace-action marketplace-action--decline" onClick={handleDeclineJob}>
                    DECLINE
                  </button>
                  <button type="button" className="marketplace-action marketplace-action--primary marketplace-action--wide" onClick={handleAcceptJob}>
                    ACCEPT &amp; NAVIGATE
                  </button>
                </div>
              </div>
            ) : (
              <div className="marketplace-dispatch__empty">
                <h3>Dispatch status updated</h3>
                <p>
                  {dispatchState === 'accepted'
                    ? `${mockSession.acceptedJob.projectTitle} accepted. ${mockSession.acceptedJob.nextStep}`
                    : 'No urgent live dispatch is currently active in your radius.'}
                </p>
              </div>
            )}
          </article>

          <article className="dash-card marketplace-card">
            <div className="marketplace-section-head">
              <p className="marketplace-kicker">Schedule Queue</p>
              <h2>Your upcoming schedule</h2>
            </div>

            <div className="marketplace-table-wrap">
              <table className="marketplace-table">
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Home Address</th>
                    <th>Scheduled Timestamp</th>
                    <th>Project Details</th>
                  </tr>
                </thead>
                <tbody>
                  {mockSession.upcomingSchedule.map((booking) => (
                    <tr key={`${booking.customerName}-${booking.scheduledTimestamp}`}>
                      <td>{booking.customerName}</td>
                      <td>{booking.homeAddress}</td>
                      <td>{booking.scheduledTimestamp}</td>
                      <td>{booking.projectDetails}</td>
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