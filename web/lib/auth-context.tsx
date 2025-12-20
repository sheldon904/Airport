'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api } from './api';
import type { User, TokenResponse } from '@/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    organization_name: string;
    admin_email: string;
    admin_password: string;
    admin_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check for existing session
    const checkAuth = async () => {
      const token = api.getAccessToken();
      if (token) {
        try {
          const userData = await api.getCurrentUser();
          setUser(userData);
        } catch {
          api.clearTokens();
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    api.setTokens(tokens);
    const userData = await api.getCurrentUser();
    setUser(userData);
    router.push('/dashboard');
  };

  const register = async (data: {
    organization_name: string;
    admin_email: string;
    admin_password: string;
    admin_name: string;
  }) => {
    const response = await api.register(data);
    api.setTokens(response.tokens);
    setUser(response.user);
    router.push('/dashboard');
  };

  const logout = () => {
    api.clearTokens();
    setUser(null);
    router.push('/auth/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
