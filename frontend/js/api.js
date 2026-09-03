/**
 * Centralized API Client for Student OD & Leave Approval System
 */

const API_BASE = '/api';

const API = {
  getToken() {
    return localStorage.getItem('od_leave_auth_token');
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('od_leave_auth_token', token);
    } else {
      localStorage.removeItem('od_leave_auth_token');
    }
  },

  getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem('od_leave_user_info'));
    } catch {
      return null;
    }
  },

  setCurrentUser(user) {
    if (user) {
      localStorage.setItem('od_leave_user_info', JSON.stringify(user));
    } else {
      localStorage.removeItem('od_leave_user_info');
    }
  },

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = options.headers || {};
    
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // If body is not FormData, default to application/json
    if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }

    options.headers = headers;

    try {
      const response = await fetch(url, options);

      // Handle CSV or Blob response
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/csv')) {
        return response.blob();
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        if (response.status === 401) {
          // Auto logout on unauthorized
          this.logout();
        }
        throw new Error(data.error || data.message || `Request failed with status ${response.status}`);
      }

      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // HTTP Helper Methods
  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const url = query ? `${endpoint}?${query}` : endpoint;
    return this.request(url, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, { method: 'POST', body });
  },

  put(endpoint, body) {
    return this.request(endpoint, { method: 'PUT', body });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },

  logout() {
    this.setToken(null);
    this.setCurrentUser(null);
    window.location.reload();
  }
};
