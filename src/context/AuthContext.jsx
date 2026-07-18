import React, { createContext, useState, useEffect, useContext } from "react";
import { api, getTokens, saveTokens, clearTokens } from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem("samvridhitantu_lang") || "en";
  });

  // Verify access token and get user profile
  const fetchCurrentUser = async () => {
    const tokens = getTokens();
    if (!tokens) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await api.get("/auth/me");
      setUser(userData);
      if (userData.language_pref) {
        setLanguage(userData.language_pref);
        localStorage.setItem("samvridhitantu_lang", userData.language_pref);
      }
    } catch (err) {
      console.error("Failed to fetch profile:", err);
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();

    // Listen for logout events dispatched by the API interceptor
    const handleLogoutEvent = () => {
      localStorage.clear();
      sessionStorage.clear();
      setUser(null);
      clearTokens();
    };

    window.addEventListener("samvridhitantu_logout", handleLogoutEvent);
    return () => {
      window.removeEventListener("samvridhitantu_logout", handleLogoutEvent);
    };
  }, []);

  const login = async (phone_number, password) => {
    setError(null);
    setLoading(true);
    try {
      const response = await api.post("/auth/login", { phone_number, password });
      saveTokens(response);
      setUser(response.user);
      if (response.user.language_pref) {
        setLanguage(response.user.language_pref);
        localStorage.setItem("samvridhitantu_lang", response.user.language_pref);
      }
      return response.user;
    } catch (err) {
      setError(err.message || "Login failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData) => {
    setError(null);
    setLoading(true);
    try {
      const response = await api.post("/auth/register", userData);
      return response;
    } catch (err) {
      setError(err.message || "Registration failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.clear();
    sessionStorage.clear();
    clearTokens();
    setUser(null);
  };

  const updateLanguage = (lang) => {
    setLanguage(lang);
    localStorage.setItem("samvridhitantu_lang", lang);
    if (user) {
      // Opt-in: notify backend if possible, or keep local
      api.patch("/auth/me", { language_pref: lang }).catch(() => {});
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        language,
        login,
        register,
        logout,
        updateLanguage,
        clearError,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => useContext(AuthContext);
