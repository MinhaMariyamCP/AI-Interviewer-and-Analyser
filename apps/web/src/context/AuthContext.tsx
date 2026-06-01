'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface AuthContextType {
  user: any;
  login: (email: string, pass: string) => Promise<void>;
  signup: (email: string, pass: string, name: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<any>(null);
  const router = useRouter();
  const api_url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const readErrorMessage = async (res: Response, fallback: string) => {
    try {
      const data = await res.json();
      return data?.detail || fallback;
    } catch {
      return fallback;
    }
  };

  const refreshUser = async () => {
    try {
      const response = await api.get('/api/v1/users/me');
      setUser(response.data);
    } catch (err) {
      console.error("Failed to refresh user profile", err);
    }
  };

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      refreshUser();
    }
  }, []);

  const login = async (email: string, pass: string) => {
    const formData = new FormData();
    formData.append('username', email.trim().toLowerCase());
    formData.append('password', pass);

    const res = await fetch(`${api_url}/api/v1/auth/login`, {
      method: 'POST',
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('role', data.role);
      await refreshUser();
      router.push('/dashboard');
    } else {
      throw new Error(await readErrorMessage(res, 'Invalid email or password. Please try again.'));
    }
  };

  const signup = async (email: string, pass: string, name: string) => {
    const res = await fetch(`${api_url}/api/v1/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password: pass, full_name: name.trim() }),
    });

    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('role', data.role);
      await refreshUser();
      router.push('/dashboard');
    } else {
      throw new Error(await readErrorMessage(res, 'Signup failed. Please try again.'));
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, isAuthenticated: !!user, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
