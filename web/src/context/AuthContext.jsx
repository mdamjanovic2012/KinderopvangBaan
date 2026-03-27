"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { loginRequest, registerRequest, getMeRequest, refreshRequest } from "@/lib/auth";

const AuthContext = createContext(null);

const ACCESS_KEY = "kb_access";
const REFRESH_KEY = "kb_refresh";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchWorkerProfile(token) {
  const res = await fetch(`${BASE_URL}/auth/worker-profile/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json();
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
    setProfile(null);
  }, []);

  const loadProfile = useCallback(async (me) => {
    if (me?.role === "worker") {
      const p = await fetchWorkerProfile(localStorage.getItem(ACCESS_KEY));
      setProfile(p);
    } else {
      setProfile(null);
    }
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
      .then(async (me) => { setUser(me); await loadProfile(me); })
      .catch(async () => {
        try {
          const { access: newAccess } = await refreshRequest(refresh);
          localStorage.setItem(ACCESS_KEY, newAccess);
          const me = await getMeRequest(newAccess);
          setUser(me);
          await loadProfile(me);
        } catch {
          logout();
        }
      })
      .finally(() => setLoading(false));
  }, [logout, loadProfile]);

  const login = async (username, password) => {
    const { access, refresh } = await loginRequest(username, password);
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    const me = await getMeRequest(access);
    setUser(me);
    await loadProfile(me);
    return me;
  };

  const register = async ({
    username, email, password, role,
    first_name = "", last_name = "",
    opvangtype = [], kdv_proof_required = false, bso_proof_required = false,
  }) => {
    await registerRequest({
      username, email, password, role, first_name, last_name,
      opvangtype, kdv_proof_required, bso_proof_required,
    });
    return login(username, password);
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
