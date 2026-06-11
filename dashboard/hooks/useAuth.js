import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

export function useAuth() {
  const [apiKey, setApiKeyState] = useState(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKeyState(localStorage.getItem("dg_api_key"));
    }
  }, []);

  const setApiKey = (key) => {
    if (typeof window !== "undefined") {
      if (key) {
        localStorage.setItem("dg_api_key", key);
      } else {
        localStorage.removeItem("dg_api_key");
      }
      setApiKeyState(key);
    }
  };

  const clearAuth = () => {
    setApiKey(null);
  };

  const isAuthenticated = !!apiKey;

  return { apiKey, setApiKey, clearAuth, isAuthenticated };
}

export function withAuth(Component) {
  return function ProtectedRoute(props) {
    const router = useRouter();
    const [verified, setVerified] = useState(false);

    useEffect(() => {
      if (typeof window !== "undefined") {
        const key = localStorage.getItem("dg_api_key");
        if (!key) {
          router.replace("/login");
        } else {
          setVerified(true);
        }
      }
    }, [router]);

    if (!verified) {
      return (
        <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-10 h-10 border-4 border-[#58a6ff] border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm text-[#7d8590] animate-pulse">Checking credentials...</span>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
}
