"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { loginRequest, registerRequest, getMeRequest, refreshRequest } from "@/lib/auth";

const AuthContext = createContext(null);

const ACCESS_KEY = "kb_access";
const REFRESH_KEY = "kb_refresh";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
  }, []);

  // Try to restore session on mount
  useEffect(() => {
    const access = localStorage.getItem(ACCESS_KEY);
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!access || !refresh) {
      setLoading(false);
      return;
    }

    getMeRequest(access)
      .then(setUser)
      .catch(async () => {
        // Access expired — try refresh
        try {
          const { access: newAccess } = await refreshRequest(refresh);
          localStorage.setItem(ACCESS_KEY, newAccess);
          const me = await getMeRequest(newAccess);
          setUser(me);
        } catch {
          logout();
        }
      })
      .finally(() => setLoading(false));
  }, [logout]);

  const login = async (username, password) => {
    const { access, refresh } = await loginRequest(username, password);
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    const me = await getMeRequest(access);
    setUser(me);
    return me;
  };

  const register = async ({ username, email, password, role }) => {
    await registerRequest({ username, email, password, role });
    return login(username, password);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
