import axios from 'axios';

// Pull the backend URL from .env, or fallback to local port 8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export default api;
