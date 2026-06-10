import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export const AuthProvider = ({ children }) => {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('admin_token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchAdminInfo();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchAdminInfo = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/me`);
      setAdmin(response.data);
    } catch (error) {
      console.error('Failed to fetch admin info:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (emailOrUsername, password) => {
    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        username_or_email: emailOrUsername,
        password
      });
      
      const { access_token, admin } = response.data;
      localStorage.setItem('admin_token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setToken(access_token);
      setAdmin(admin);
      
      return { success: true, admin };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      };
    }
  };

  const setSessionFromSignup = ({ access_token, admin: newAdmin }) => {
    localStorage.setItem('admin_token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setToken(access_token);
    setAdmin(newAdmin);
  };

  const logout = () => {
    localStorage.removeItem('admin_token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setAdmin(null);
  };

  return (
    <AuthContext.Provider value={{ admin, login, logout, loading, setSessionFromSignup, refresh: fetchAdminInfo }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
