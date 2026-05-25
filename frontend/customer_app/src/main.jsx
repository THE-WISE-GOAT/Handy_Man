import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
// This links your CSS directly into your compiled app
import '../../shared/styles/global.css' 

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)