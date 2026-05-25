import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
// This links the exact same beautiful styles you just wrote to the worker app
import '../../shared/styles/global.css' 

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)