import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx'
import { AuthProvider } from '@shared/context/AuthContext';
// This links your CSS directly into your compiled app
import '../../shared/styles/global.css'

// Render runtime errors to the screen instead of a blank black page so the
// actual cause is visible. Without this, an uncaught render/effect throw
// unmounts the whole React tree and the user just sees a black void.
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: '#FF8A8E', background: '#0D0D0D', minHeight: '100vh' }}>
          <h2>Application error</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
            {String((this.state.error && this.state.error.stack) || this.state.error)}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)
