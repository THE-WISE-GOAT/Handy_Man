export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const LOGIN_URL = `${API_BASE_URL}/login/`;
export const REGISTER_URL = `${API_BASE_URL}/auth/register`;