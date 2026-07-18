import React, { useState, useEffect } from "react";
import { AuthProvider, useAuthContext } from "./context/AuthContext";
import Login from "./pages/auth/Login";
import Dashboard from "./pages/weaver/Dashboard";
import { RefreshCw, AlertCircle, X } from "lucide-react";

function NavigationWrapper() {
  const { isAuthenticated, loading } = useAuthContext();
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const handleToast = (e) => {
      setToast(e.detail);
      // Dismiss toast after 5 seconds
      const timer = setTimeout(() => {
        setToast(null);
      }, 5000);
      return () => clearTimeout(timer);
    };

    window.addEventListener("samvridhitantu_toast", handleToast);
    return () => {
      window.removeEventListener("samvridhitantu_toast", handleToast);
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white space-y-4">
        <RefreshCw className="w-10 h-10 animate-spin text-amber-400" />
        <p className="text-sm font-semibold tracking-wider text-slate-400">
          Initializing ArtisanEdge...
        </p>
      </div>
    );
  }

  return (
    <>
      {isAuthenticated ? <Dashboard /> : <Login />}

      {/* Global Toast System */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-[9999] max-w-sm w-full bg-slate-900/95 border border-red-500/30 backdrop-blur-md rounded-xl p-4 shadow-2xl flex items-start gap-3 animate-slideIn">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">Network Warning</h4>
            <p className="text-xs text-slate-300 mt-0.5">{toast.message}</p>
          </div>
          <button 
            onClick={() => setToast(null)} 
            className="text-slate-500 hover:text-white cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationWrapper />
    </AuthProvider>
  );
}
