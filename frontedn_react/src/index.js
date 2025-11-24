import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/index.css'; // Make sure this path matches your actual file location
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);