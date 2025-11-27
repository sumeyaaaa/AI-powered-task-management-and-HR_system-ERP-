import axios from 'axios';
import { config } from '../utils/constants';

// For local development, always use localhost:5000
// Override any deployment URLs when running on localhost:3000
const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:5000' : (process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:5000');

console.log('API Base URL:', API_BASE_URL);
console.log('Is Local Dev:', isLocalDev);

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL, // Use API_BASE_URL directly, not config.BACKEND_URL
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    console.log('Making API request:', {
      url: config.url,
      method: config.method,
      baseURL: config.baseURL
    });
    
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors
api.interceptors.response.use(
  (response) => {
    console.log('API response received:', {
      url: response.config.url,
      status: response.status
    });
    return response;
  },
  (error) => {
    console.error('API response error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message
    });
    
    if (error.response?.status === 401) {
      // Unauthorized - clear local storage and redirect to login
      // Only redirect if we're not already on the login page
      if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
        localStorage.removeItem('token');
        localStorage.removeItem('userData');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export { api };