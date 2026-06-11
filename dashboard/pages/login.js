import React, { useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { toast } from 'react-hot-toast';
import { Key, Mail, User, Copy, Check, Eye, EyeOff, Layers, AlertCircle } from 'lucide-react';
import { registerUser, getMe } from '../lib/api';

export default function Login() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('register'); // 'register' | 'signin'
  
  // Registration state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [registeredKey, setRegisteredKey] = useState('');
  const [copied, setCopied] = useState(false);

  // Sign In state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regName.trim() || !regEmail.trim()) {
      setErrorMsg('Full Name and Email are required.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const data = await registerUser(regEmail.trim(), regName.trim());
      const api_key = data.api_key;
      setRegisteredKey(api_key);
      localStorage.setItem("dg_api_key", api_key);
      toast.success('Account registered successfully!');
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || 'Failed to create account.');
      toast.error('Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) {
      setErrorMsg('API Key is required.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    
    // Temporarily set the key in localStorage to validate it with getMe()
    const tempKey = apiKeyInput.trim();
    localStorage.setItem("dg_api_key", tempKey);

    try {
      // Validate by querying getMe
      await getMe();
      toast.success('Successfully signed in!');
      router.replace('/dashboard');
    } catch (err) {
      console.error(err);
      // Clear key if validation fails
      localStorage.removeItem("dg_api_key");
      setErrorMsg(err.message || 'Invalid API Key. Please try again.');
      toast.error('Sign In failed.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (navigator.clipboard && registeredKey) {
      navigator.clipboard.writeText(registeredKey);
      setCopied(true);
      toast.success('API Key copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-6 relative font-sans antialiased text-[#e6edf3]">
      <Head>
        <title>DriftGuard Console Setup</title>
        <meta name="description" content="Set up credentials or login to DriftGuard MLOps observability platform." />
      </Head>

      <div className="max-w-md w-full flex flex-col space-y-6 relative z-10">
        {/* Brand header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <span className="p-3 bg-gradient-to-tr from-[#58a6ff] to-[#a371f7] rounded-xl shadow-inner text-[#0d1117]">
            <Layers className="w-6 h-6" />
          </span>
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-teal-400 to-[#58a6ff] bg-clip-text text-transparent">
            DRIFTGUARD CONSOLE
          </h1>
          <p className="text-[10px] text-[#7d8590] uppercase tracking-widest font-semibold">
            Autonomous Model Health Platform
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-[#1c2128] border border-[#30363d] rounded-lg shadow-2xl overflow-hidden relative min-h-[300px]">
          {/* Error Banner */}
          {errorMsg ? (
            <div className="bg-[#3d1515] border-b border-[#5a1e1e] px-4 py-3 flex items-start space-x-2 text-xs text-[#f85149] animate-pulse-slow">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          ) : null}

          {/* Success Registration Panel */}
          {registeredKey ? (
            <div className="p-6 space-y-6">
              <div className="text-center space-y-2">
                <h3 className="text-base font-bold text-[#3fb950]">Credentials Generated!</h3>
                <p className="text-xs text-[#7d8590] leading-relaxed">
                  Your DriftGuard API Key is displayed below. Copy this key immediately. You will not be able to retrieve it again.
                </p>
              </div>

              {/* Display Key */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-[#0d1117] border border-[#30363d] font-mono text-xs text-[#e6edf3] break-all select-all relative group">
                <span className="pr-4">{registeredKey}</span>
                <button
                  onClick={copyToClipboard}
                  className="p-1.5 rounded-lg border border-[#30363d] bg-[#21262d] hover:bg-[#30363d] hover:text-[#58a6ff] text-[#7d8590] transition-all flex-shrink-0"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#3fb950]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>

              <button
                onClick={() => router.replace('/dashboard')}
                className="w-full py-2.5 rounded-lg bg-[#58a6ff] hover:bg-[#58a6ff]/80 text-[#0d1117] text-xs font-bold transition-all active:scale-95 flex items-center justify-center space-x-2"
              >
                <span>Go to Dashboard</span>
              </button>
            </div>
          ) : (
            <>
              {/* Card Tabs */}
              <div className="flex border-b border-[#30363d] bg-[#161b22]/40">
                <button
                  onClick={() => {
                    setActiveTab('register');
                    setErrorMsg('');
                  }}
                  className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all ${
                    activeTab === 'register'
                      ? 'border-[#58a6ff] text-[#e6edf3] bg-[#1c2128]/25'
                      : 'border-transparent text-[#7d8590] hover:text-[#e6edf3]'
                  }`}
                >
                  Register
                </button>
                <button
                  onClick={() => {
                    setActiveTab('signin');
                    setErrorMsg('');
                  }}
                  className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all ${
                    activeTab === 'signin'
                      ? 'border-[#58a6ff] text-[#e6edf3] bg-[#1c2128]/25'
                      : 'border-transparent text-[#7d8590] hover:text-[#e6edf3]'
                  }`}
                >
                  Sign In
                </button>
              </div>

              {/* Form Content */}
              <div className="p-6">
                {activeTab === 'register' ? (
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-[#7d8590] uppercase tracking-wider block">
                        Full Name
                      </label>
                      <div className="relative">
                        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#7d8590]">
                          <User className="w-4 h-4" />
                        </span>
                        <input
                          type="text"
                          required
                          placeholder="e.g. John Doe"
                          value={regName}
                          onChange={(e) => setRegName(e.target.value)}
                          className="w-full pl-10 pr-4 py-2 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-[#e6edf3] placeholder-[#7d8590] focus:outline-none focus:border-[#58a6ff] transition-colors"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-[#7d8590] uppercase tracking-wider block">
                        Email Address
                      </label>
                      <div className="relative">
                        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#7d8590]">
                          <Mail className="w-4 h-4" />
                        </span>
                        <input
                          type="email"
                          required
                          placeholder="e.g. name@company.com"
                          value={regEmail}
                          onChange={(e) => setRegEmail(e.target.value)}
                          className="w-full pl-10 pr-4 py-2 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-[#e6edf3] placeholder-[#7d8590] focus:outline-none focus:border-[#58a6ff] transition-colors"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-2.5 rounded-lg bg-[#58a6ff] hover:bg-[#58a6ff]/80 text-[#0d1117] text-xs font-bold transition-all disabled:opacity-50 active:scale-95 mt-2 flex items-center justify-center cursor-pointer"
                    >
                      {loading ? (
                        <div className="w-4 h-4 border-2 border-[#0d1117] border-t-transparent rounded-full animate-spin"></div>
                      ) : (
                        'Create Account & Get API Key'
                      )}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleSignIn} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-semibold text-[#7d8590] uppercase tracking-wider block">
                        DriftGuard API Key
                      </label>
                      <div className="relative">
                        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#7d8590]">
                          <Key className="w-4 h-4" />
                        </span>
                        <input
                          type={showPassword ? 'text' : 'password'}
                          required
                          placeholder="dg-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          className="w-full pl-10 pr-10 py-2 rounded-lg bg-[#0d1117] border border-[#30363d] text-xs text-[#e6edf3] placeholder-[#7d8590] focus:outline-none focus:border-[#58a6ff] transition-colors"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#7d8590] hover:text-[#e6edf3] cursor-pointer"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-2.5 rounded-lg bg-[#58a6ff] hover:bg-[#58a6ff]/80 text-[#0d1117] text-xs font-bold transition-all disabled:opacity-50 active:scale-95 mt-2 flex items-center justify-center cursor-pointer"
                    >
                      {loading ? (
                        <div className="w-4 h-4 border-2 border-[#0d1117] border-t-transparent rounded-full animate-spin"></div>
                      ) : (
                        'Sign In'
                      )}
                    </button>
                  </form>
                )}


              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
