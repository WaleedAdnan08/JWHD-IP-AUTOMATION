'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/axios';

interface User {
  id: string;
  email: string;
  full_name: string;
  firm_affiliation?: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      console.log('AuthContext: Initializing...');
      const token = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');

      if (token && storedUser) {
        console.log('AuthContext: Found token and user in localStorage');
        try {
          setUser(JSON.parse(storedUser));
        } catch (error) {
          console.error("AuthContext: Failed to parse user data", error);
          logout();
        }
      } else {
        console.log('AuthContext: No complete session in localStorage, checking cookies...');
        // Fallback: Check for cookie-based session if local storage is empty
        // This handles cases where middleware passes the user through (valid cookie)
        // but local storage is empty/cleared
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
          const parts = cookie.trim().split('=');
          if (parts.length >= 2) {
             const key = parts[0];
             const value = parts.slice(1).join('=');
             acc[key] = value;
          }
          return acc;
        }, {} as Record<string, string>);

        console.log('AuthContext: Cookies found:', cookies);

        if (cookies.token) {
          console.log('AuthContext: Found token cookie, attempting to restore session...');
          try {
            // Restore session from server
            const response = await api.get('/auth/me', {
              headers: { Authorization: `Bearer ${cookies.token}` }
            });
            console.log('AuthContext: Session restored successfully', response.data);
            
            // Re-sync local storage
            localStorage.setItem('token', cookies.token);
            localStorage.setItem('user', JSON.stringify(response.data));
            setUser(response.data);
          } catch (error) {
            console.error("AuthContext: Failed to restore session from cookie", error);
            // If cookie is invalid, force logout to clear it and redirect to login
            logout();
          }
        } else {
           console.log('AuthContext: No token cookie found');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = (token: string, userData: User) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    // Set cookie for middleware access (expires in 7 days to match refresh token potential)
    document.cookie = `token=${token}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax`;
    setUser(userData);
    router.push('/dashboard');
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error("Logout API call failed", error);
    }

    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Remove cookie with various path/domain options to be safe
    document.cookie = 'token=; path=/; max-age=0';
    document.cookie = 'token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'token=; path=/; max-age=0; SameSite=Lax';
    
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      logout,
      isAuthenticated: !!user
    }}>
      {children}
    </AuthContext.Provider>
  );
};