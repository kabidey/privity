import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Function to refresh user permissions from the server
export const refreshUserPermissions = async () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    const response = await api.get('/auth/me');
    const userData = response.data;
    
    // Update localStorage with fresh user data including permissions
    localStorage.setItem('user', JSON.stringify(userData));
    
    // Dispatch event to notify components
    window.dispatchEvent(new Event('permissionsRefresh'));
    
    return userData;
  } catch (error) {
    console.error('Failed to refresh user permissions:', error);
    return null;
  }
};

export default api;
