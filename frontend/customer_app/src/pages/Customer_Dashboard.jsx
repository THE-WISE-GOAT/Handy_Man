import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '@shared/context/AuthContext';
import { apiClient, normalizeApiError } from '@shared/api/client';

const TAB_SEQUENCE = ['new-booking', 'in-progress', 'history', 'around-you'];

const dropdownItemStyle = {
  width: '100%',
  background: 'none',
  border: 'none',
  color: 'var(--ind-ink)',
  padding: '10px 12px',
  textAlign: 'left',
  fontSize: '0.825rem',
  cursor: 'pointer',
  borderRadius: '4px',
  transition: 'background-color 0.15s',
  display: 'block'
};

const cellStyle = {
  padding: '16px var(--ind-space-4, 1.5rem)',
  fontSize: '0.85rem'
};

export default function CustomerDashboard({ onNavigate }) {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('new-booking');
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [tags, setTags] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { sender: 'ai', text: 'What is your problem today? Describe your technical emergency for immediate dispatch.' }
  ]);
  const [activeJob, setActiveJob] = useState(null);
  const [completedTasks, setCompletedTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [workerApplicationStatus, setWorkerApplicationStatus] = useState(null);

  const chatContainerRef = useRef(null);
  const scrollDebounceRef = useRef(null);

  const profileName = user?.firstName ? `${user.firstName} ${user.lastName || ''}`.trim() : user?.username || 'Client Profile';
  const profileLocation = user?.locationLabel || '📍 System Location Active';
  const accountType = user?.accountType || 'Customer';

  useEffect(() => {
    const fetchTasks = async () => {
      if (!user) return;
      setIsLoadingTasks(true);
      try {
        const tasks = await apiClient.get('/service-tasks/');
        const openTask = tasks.find(t => t.status === 'open' || t.status === 'matched');
        const completed = tasks.filter(t => t.status === 'completed');
        setActiveJob(openTask ? {
          title: openTask.problem_description,
          assignedWorker: openTask.assigned_worker ? `Technician: ${openTask.assigned_worker}` : 'Unassigned',
          status: openTask.status === 'matched' ? 'Assigned' : 'Pending',
          requestedAt: new Date(openTask.created_at).toLocaleDateString(),
          eta: openTask.eta || 'TBD',
          pipeline: [
            { label: 'Requested', state: 'done' },
            { label: 'Matched', state: openTask.status === 'matched' ? 'done' : openTask.status === 'open' ? 'active' : 'pending' },
            { label: 'In Progress', state: openTask.status === 'matched' ? 'active' : 'pending' },
            { label: 'Completed', state: completed.length > 0 ? 'done' : 'pending' }
          ]
        } : null);
        setCompletedTasks(completed.map(t => ({
          date: new Date(t.created_at).toISOString().split('T')[0],
          serviceType: t.problem_description,
          providerName: t.assigned_worker || 'Pending Assignment',
          cost: t.amount ? `रू ${t.amount}` : 'N/A',
          receiptHref: `#download-receipt-${t.id}`
        })));
      } catch (error) {
        console.warn('Could not fetch tasks:', error);
      } finally {
        setIsLoadingTasks(false);
      }
    };
    fetchTasks();
  }, [user]);

  const handleOuterGlobalScroll = useCallback((e) => {
    if (scrollDebounceRef.current) return;

    if (chatContainerRef.current && chatContainerRef.current.contains(e.target)) {
      return;
    }

    e.preventDefault();
    scrollDebounceRef.current = setTimeout(() => {
      scrollDebounceRef.current = null;
    }, 400);

    const currentIdx = TAB_SEQUENCE.indexOf(activeTab);

    if (e.deltaY > 0) {
      if (currentIdx < TAB_SEQUENCE.length - 1) {
        setActiveTab(TAB_SEQUENCE[currentIdx + 1]);
      }
    } else {
      if (currentIdx > 0) {
        setActiveTab(TAB_SEQUENCE[currentIdx - 1]);
      }
    }
  }, [activeTab]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || !user) return;

    const userMessage = { sender: 'user', text: chatInput };
    const baseFeed = [...chatMessages, userMessage];
    setChatMessages(baseFeed);
    setChatInput('');

    try {
      const response = await apiClient.post('/chat/message', {
        message: chatInput
      });
      setChatMessages([
        ...baseFeed,
        { sender: 'ai', text: response.response || 'Diagnostic logged. Processing your request...' }
      ]);
      setTags(prev => {
        const newTags = [...prev];
        if (chatInput.toLowerCase().includes('plumb')) {
          if (!newTags.includes('Plumber')) newTags.push('Plumber');
        }
        if (chatInput.toLowerCase().includes('electric')) {
          if (!newTags.includes('Electrician')) newTags.push('Electrician');
        }
        if (chatInput.toLowerCase().includes('urgent') || chatInput.toLowerCase().includes('emergency')) {
          if (!newTags.includes('Emergency')) newTags.push('Emergency');
        }
        return newTags.filter((t, i, arr) => arr.indexOf(t) === i);
      });
    } catch (error) {
      setChatMessages([
        ...baseFeed,
        { sender: 'ai', text: 'Diagnostic logged. I have pinned appropriate categorization markers onto your tracking dashboard configuration panel.' }
      ]);
    }
  };

  const removeTag = (tagToRemove) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  const handleLogoutClick = async () => {
    try {
      if (logout) await logout();
      onNavigate('login');
    } catch (err) {
      console.error('Logout error routine:', err);
    }
  };

  const handleWorkerApplication = async () => {
    try {
      const response = await apiClient.post('/workers/apply', {});
      setWorkerApplicationStatus(response.message);
      alert('Worker role applied successfully! You can now access the service specialist dashboard.');
    } catch (error) {
      setWorkerApplicationStatus('Failed to apply for worker role');
      alert('Could not apply for worker role. Please try again.');
    }
  };

  return (
    <div className="stitched-dashboard-canvas" onWheel={handleOuterGlobalScroll}>
      <div className="stitched-window-chassis">
        
        <div className="stitched-tab-bar">
          
          <button style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px 8px',
            marginBottom: '10px',
            marginRight: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            color: 'var(--ind-muted)'
          }}>
            <svg width="20" height="14" viewBox="0 0 18 12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="1.5" y1="1.5" x2="16.5" y2="1.5" />
              <line x1="1.5" y1="6" x2="16.5" y2="6" />
              <line x1="1.5" y1="10.5" x2="16.5" y2="10.5" />
            </svg>
          </button>

          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '100%' }}>
            {[
              { id: 'new-booking', label: 'New Booking', icon: '+' },
              { id: 'in-progress', label: 'In Progress', icon: '⌛' },
              { id: 'history', label: 'History', icon: '📜' },
              { id: 'around-you', label: 'Around You', icon: '📍' }
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    border: '1px solid var(--ind-border)',
                    borderBottom: 'none',
                    borderTopLeftRadius: '6px',
                    borderTopRightRadius: '6px',
                    padding: '0 20px',
                    height: isActive ? '50px' : '40px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '700',
                    backgroundColor: isActive ? 'var(--ind-surface)' : 'var(--ind-charcoal-soft)',
                    color: isActive ? 'var(--ind-ink)' : 'var(--ind-muted)',
                    position: 'relative',
                    zIndex: isActive ? 5 : 1,
                    transition: 'all 0.2s ease-in-out'
                  }}
                >
                  <span style={{ fontSize: '0.95rem' }}>{tab.icon}</span>
                  <span style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    display: 'inline-block',
                    maxWidth: isActive ? '130px' : '0px',
                    opacity: isActive ? 1 : 0,
                    transition: 'max-width 0.25s ease-in-out, opacity 0.2s ease-in-out'
                  }}>
                    {tab.label}
                  </span>
                  
                  {isActive && (
                    <div style={{
                      position: 'absolute',
                      bottom: '-2px',
                      left: 0,
                      right: 0,
                      height: '4px',
                      backgroundColor: 'var(--ind-surface)',
                      zIndex: 6
                    }} />
                  )}
                </button>
              );
            })}
          </div>

          <div style={{ marginLeft: 'auto', marginBottom: '10px', position: 'relative', zIndex: 20 }}>
            <button 
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--ind-charcoal-soft)',
                border: '1px solid var(--ind-border)',
                borderRadius: '20px',
                padding: '6px 16px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: '600'
              }}
            >
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#27ae60' }} />
              <span>{user?.firstName || user?.username || 'Account'}</span>
              <span style={{ fontSize: '0.65rem' }}>▼</span>
            </button>

            {isProfileOpen && (
              <div style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                width: '240px',
                backgroundColor: 'var(--ind-surface)',
                border: '1px solid var(--ind-border)',
                borderRadius: '8px',
                padding: '6px',
                boxShadow: 'var(--ind-shadow)',
                zIndex: 100
              }}>
                <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--ind-grid-line-strong)', marginBottom: '6px' }}>
                  <p style={{ margin: 0, fontSize: '0.85rem', fontWeight: '700', color: 'var(--ind-ink)' }}>{profileName}</p>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--ind-muted)' }}>{profileLocation}</p>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.7rem', color: 'var(--ind-amber)', fontWeight: '600' }}>{accountType}</p>
                </div>
                <button onClick={() => alert('Configuration profiles loaded.')} style={dropdownItemStyle}>⚙️ System Settings</button>
                <button onClick={() => alert('Styles updated.')} style={dropdownItemStyle}>🎨 Interface Customization</button>
                <div style={{ height: '1px', backgroundColor: 'var(--ind-grid-line-strong)', margin: '6px 0' }} />
                <button onClick={handleLogoutClick} style={{ ...dropdownItemStyle, color: '#dc3545', fontWeight: '700' }}>
                  🚪 Disconnect Account
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="stitched-main-container">
          
          {activeTab === 'new-booking' && (
            <div style={{ display: 'flex', flex: 1, width: '100%', height: '100%' }}>
              
              <div style={{ width: '70%', display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--ind-border)' }}>
                <div 
                  ref={chatContainerRef}
                  className="stitched-scroll-pane" 
                  style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
                >
                  {chatMessages.map((msg, index) => (
                    <div key={index} style={{ display: 'flex', justifyContent: msg.sender === 'ai' ? 'flex-start' : 'flex-end' }}>
                      <div style={{
                        maxWidth: '65%',
                        padding: '12px 18px',
                        borderRadius: '16px',
                        fontSize: '0.88rem',
                        lineHeight: '1.5',
                        backgroundColor: msg.sender === 'ai' ? 'var(--ind-concrete)' : 'var(--ind-charcoal)',
                        color: msg.sender === 'ai' ? 'var(--ind-ink)' : 'var(--ind-white)',
                        border: '1px solid var(--ind-border)'
                      }}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleSendMessage} style={{ padding: '1.5rem', borderTop: '1px solid var(--ind-border)', backgroundColor: 'var(--ind-surface)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', backgroundColor: 'var(--ind-concrete)', padding: '10px 18px', borderRadius: '30px', border: '1px solid var(--ind-border)' }}>
                    <input 
                      type="text" 
                      placeholder="Type a message describing your technical emergency request..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      disabled={!user}
                      style={{ flex: 1, background: 'none', border: 'none', color: 'var(--ind-ink)', fontSize: '0.88rem', outline: 'none' }}
                    />
                    <button type="submit" disabled={!user || !chatInput.trim()} style={{
                      backgroundColor: 'var(--ind-charcoal)',
                      border: 'none',
                      color: 'var(--ind-white)',
                      padding: '8px 20px',
                      borderRadius: '20px',
                      cursor: 'pointer',
                      fontWeight: '700',
                      fontSize: '0.8rem'
                    }}>SEND</button>
                  </div>
                </form>
              </div>

              <div style={{ width: '30%', padding: '2rem', backgroundColor: 'var(--ind-surface)' }} className="stitched-scroll-pane">
                <h4 style={{ margin: '0 0 1.25rem 0', fontSize: '0.75rem', fontWeight: '800', color: 'var(--ind-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                  Live Classification Tags
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {tags.map((tag) => (
                    <div key={tag} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      backgroundColor: 'var(--ind-concrete)',
                      border: '1px solid var(--ind-border-strong)',
                      color: 'var(--ind-ink)',
                      padding: '6px 12px',
                      borderRadius: '20px',
                      fontSize: '0.75rem',
                      fontWeight: '600'
                    }}>
                      <span>{tag}</span>
                      <button 
                        type="button" 
                        onClick={() => removeTag(tag)}
                        style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem', padding: 0 }}
                      >✕</button>
                    </div>
                  ))}
                  {tags.length === 0 && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--ind-muted)', fontStyle: 'italic' }}>No tracking variables detected.</p>
                  )}
                </div>

                <div style={{ marginTop: '2rem' }}>
                  <button
                    onClick={handleWorkerApplication}
                    style={{
                      width: '100%',
                      padding: '12px 16px',
                      backgroundColor: 'var(--ind-amber)',
                      color: 'var(--ind-charcoal)',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: '700',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px'
                    }}
                  >
                    🛠 Join Us as a Worker
                  </button>
                  {workerApplicationStatus && (
                    <p style={{ fontSize: '0.75rem', color: 'var(--ind-muted)', marginTop: '8px' }}>{workerApplicationStatus}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'in-progress' && (
            <div style={{ padding: '3rem', flex: 1 }} className="stitched-scroll-pane">
              <div style={{ borderBottom: '1px solid var(--ind-border)', paddingBottom: '1.25rem', marginBottom: '2rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--ind-muted)', fontWeight: '800', textTransform: 'uppercase' }}>Active Request Queue</span>
                <h2 style={{ margin: '6px 0 0 0', fontSize: '1.6rem', color: 'var(--ind-ink)', fontWeight: '500' }}>
                  {activeJob ? activeJob.title : 'No Active Jobs'}
                </h2>
              </div>

              {activeJob ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
                    <div style={{ backgroundColor: 'var(--ind-concrete)', padding: '16px', borderRadius: '8px', border: '1px solid var(--ind-border)' }}>
                      <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--ind-muted)', textTransform: 'uppercase' }}>Dispatched Personnel</p>
                      <p style={{ margin: '6px 0 0 0', fontSize: '0.95rem', fontWeight: '700' }}>{activeJob.assignedWorker}</p>
                    </div>
                    <div style={{ backgroundColor: 'var(--ind-concrete)', padding: '16px', borderRadius: '8px', border: '1px solid var(--ind-border)' }}>
                      <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--ind-muted)', textTransform: 'uppercase' }}>Arrival Estimation</p>
                      <p style={{ margin: '6px 0 0 0', fontSize: '0.95rem', fontWeight: '700', color: 'var(--ind-amber)' }}>{activeJob.eta}</p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px', padding: '16px', backgroundColor: 'var(--ind-concrete)', borderRadius: '8px' }}>
                    {activeJob.pipeline.map((step, idx) => (
                      <div key={step.label} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{
                          padding: '6px 14px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          backgroundColor: step.state === 'done' ? '#eafaf1' : step.state === 'active' ? 'var(--ind-charcoal)' : '#fff',
                          color: step.state === 'done' ? '#27ae60' : step.state === 'active' ? '#fff' : 'var(--ind-muted)',
                          border: '1px solid var(--ind-border)'
                        }}>
                          {step.label}
                        </div>
                        {idx < activeJob.pipeline.length - 1 && <span style={{ color: 'var(--ind-border-strong)' }}>➔</span>}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--ind-muted)' }}>
                  <p>No active service tasks. Create a new booking to get started.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div style={{ padding: '3rem', flex: 1 }} className="stitched-scroll-pane">
              <div style={{ marginBottom: '2rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--ind-muted)', textTransform: 'uppercase', fontWeight: '800' }}>System Archive Registry</span>
                <h2 style={{ margin: '6px 0 0 0', fontSize: '1.6rem', color: 'var(--ind-ink)', fontWeight: '500' }}>Past Completed Orders</h2>
              </div>

              {isLoadingTasks ? (
                <p style={{ color: 'var(--ind-muted)' }}>Loading history...</p>
              ) : completedTasks.length > 0 ? (
                <div className="marketplace-table-wrap" style={{ border: '1px solid var(--ind-border)', borderRadius: '8px' }}>
                  <table className="marketplace-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--ind-concrete)', borderBottom: '1px solid var(--ind-border)' }}>
                        <th style={cellStyle}>Date</th>
                        <th style={cellStyle}>Service Type</th>
                        <th style={cellStyle}>Provider Name</th>
                        <th style={cellStyle}>Cost</th>
                        <th style={cellStyle}>Receipt</th>
                      </tr>
                    </thead>
                    <tbody>
                      {completedTasks.map((order, index) => (
                        <tr key={index} style={{ borderBottom: '1px solid var(--ind-grid-line)' }}>
                          <td style={cellStyle}>{order.date}</td>
                          <td style={{ ...cellStyle, fontWeight: '700' }}>{order.serviceType}</td>
                          <td style={cellStyle}>{order.providerName}</td>
                          <td style={cellStyle}>{order.cost}</td>
                          <td style={cellStyle}>
                            <a className="marketplace-table__link" href={order.receiptHref} onClick={(e) => e.preventDefault()}>
                              Download Receipt
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ color: 'var(--ind-muted)', fontStyle: 'italic' }}>No completed tasks found.</p>
              )}
            </div>
          )}

          {activeTab === 'around-you' && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', textAlign: 'center' }}>
              <div style={{ maxWidth: '440px' }}>
                <h3 style={{ margin: '0 0 10px 0', color: 'var(--ind-ink)', fontWeight: '500', fontSize: '1.35rem' }}>Vector Location Mapping</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--ind-muted)', lineHeight: '1.6', marginBottom: '1.5rem' }}>
                  Identify active task force distribution vectors across your current dispatch matrix environment.
                </p>
                <div style={{
                  height: '180px',
                  border: '2px dashed var(--ind-border-strong)',
                  borderRadius: '8px',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: '0.75rem',
                  color: 'var(--ind-muted)',
                  backgroundColor: 'var(--ind-concrete)'
                }}>[ Map Framework Engine Context Placeholder ]</div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
