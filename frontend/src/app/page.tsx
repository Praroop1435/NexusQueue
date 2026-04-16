"use client";

import { useState, useEffect } from "react";
import { KeyRound, ShieldAlert, Cpu, Activity, Box, Play, RefreshCw, Key, Copy, Check, X, Lock, User, LogOut } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";

type Job = {
  id: string;
  task: string;
  status: "pending" | "in_progress" | "completed";
  result?: string;
  created_at?: string;
};

type ApiKey = {
  api_key: string;
  created_at: string;
};

type ApiUsage = {
  api_key_prefix: string;
  request_count: number;
  rate_limit: number;
  window_seconds: number;
  last_reset: string;
};

export default function Dashboard() {
  // Auth State
  const [token, setToken] = useState<string | null>(null);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState("");

  // App State
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [taskInput, setTaskInput] = useState("Process large dataset");
  const [testResult, setTestResult] = useState<{ status: number; text: string; time: number } | null>(null);
  const [usage, setUsage] = useState<ApiUsage | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [newlyGeneratedKey, setNewlyGeneratedKey] = useState<string | null>(null);
  const [hasCopied, setHasCopied] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (savedToken) setToken(savedToken);
  }, []);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      const res = await fetch(`${BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      const data = await res.json();
      
      if (!res.ok) {
        if (typeof data.detail === "string") {
          setAuthError(data.detail);
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          setAuthError(data.detail[0].msg);
        } else {
          setAuthError("Authentication failed");
        }
        return;
      }
      
      if (authMode === "login") {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      } else {
        setAuthMode("login");
        setAuthError("Registration successful. Please log in.");
      }
    } catch (err) {
      setAuthError("Network error. Is the backend running?");
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setApiKeys([]);
    setSelectedKey("");
    setUsage(null);
  };

  const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setHasCopied(true);
    setTimeout(() => setHasCopied(false), 2000);
  };

  const generateKey = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${BASE_URL}/api-keys`, { 
        method: "POST",
        headers: authHeaders 
      });
      if (res.ok) {
        const data = await res.json();
        setApiKeys((prev) => [data, ...prev]);
        setSelectedKey(data.api_key);
        setNewlyGeneratedKey(data.api_key);
      } else {
        if (res.status === 401) logout();
      }
    } catch (e) {
      console.error(e);
    }
    setIsGenerating(false);
  };

  const fetchUsage = async (keyToFetch: string) => {
    if (!keyToFetch || !token) return;
    try {
      const res = await fetch(`${BASE_URL}/api-keys/${keyToFetch}/usage`, {
        headers: authHeaders
      });
      if (res.ok) {
        setUsage(await res.json());
      } else if (res.status === 401) {
        logout();
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (selectedKey) fetchUsage(selectedKey);
  }, [selectedKey]);

  const testRateLimit = async () => {
    if (!selectedKey) return;
    const start = performance.now();
    try {
      const res = await fetch(`${BASE_URL}/secure-data`, {
        headers: { "X-API-Key": selectedKey },
      });
      const end = performance.now();
      
      let text = "";
      if (res.status === 200) {
        const d = await res.json();
        text = d.message;
      } else if (res.status === 429) {
        text = "Rate Limit Exceeded (Max 5/min).";
      } else if (res.status === 401) {
        text = "Unauthorized Key.";
      } else {
        text = `Error ${res.status}`;
      }
      
      setTestResult({ status: res.status, text, time: Math.round(end - start) });
      fetchUsage(selectedKey);
    } catch (e) {
      console.error(e);
      setTestResult({ status: 0, text: "Network Error", time: 0 });
    }
  };

  const submitJob = async () => {
    try {
      const res = await fetch(`${BASE_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: taskInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setJobs((prev) => [{ id: data.job_id, task: data.task, status: "pending" }, ...prev]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const checkJobStatus = async (id: string) => {
    try {
      const res = await fetch(`${BASE_URL}/jobs/${id}`);
      if (res.ok) {
        const data = await res.json();
        setJobs((prev) =>
          prev.map((j) =>
            j.id === id ? { ...j, status: data.status, result: data.result, created_at: data.created_at } : j
          )
        );
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    const activeJobs = jobs.filter((j) => j.status !== "completed");
    if (activeJobs.length === 0) return;

    const interval = setInterval(() => {
      activeJobs.forEach((j) => checkJobStatus(j.id));
    }, 2000);
    return () => clearInterval(interval);
  }, [jobs]);

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white max-w-sm w-full p-8 rounded-2xl shadow-lg border border-slate-200">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg mx-auto mb-6">
            <Lock size={24} />
          </div>
          <h1 className="text-2xl font-bold text-center mb-2">Secure Gateway</h1>
          <p className="text-slate-500 text-center mb-8 text-sm">Sign in to provision and track API Keys</p>
          
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Email</label>
              <input 
                type="email" required
                value={authEmail} onChange={e => setAuthEmail(e.target.value)}
                className="w-full mt-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Password</label>
              <input 
                type="password" required minLength={6}
                value={authPassword} onChange={e => setAuthPassword(e.target.value)}
                className="w-full mt-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            
            {authError && <div className="text-red-500 text-sm font-medium">{authError}</div>}
            
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors mt-2">
              {authMode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>
          
          <button onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }} className="w-full text-slate-500 text-sm mt-6 hover:text-blue-600">
            {authMode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 font-sans relative">
      
      {/* SUCCESS MODAL FOR NEW API KEY */}
      {newlyGeneratedKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-6">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Credential Created</h3>
                <p className="text-sm text-slate-500 mt-1">Please copy your API key now. It will not be shown again.</p>
              </div>
              <button 
                onClick={() => setNewlyGeneratedKey(null)}
                className="text-slate-400 hover:text-slate-600 bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="relative group">
              <div className="bg-slate-50 border-2 border-slate-200 rounded-xl p-4 pr-14 break-all font-mono text-sm shadow-inner text-slate-700">
                {newlyGeneratedKey}
              </div>
              <button
                onClick={() => copyToClipboard(newlyGeneratedKey)}
                className="absolute right-2 top-2 bottom-2 bg-white border border-slate-200 hover:border-blue-500 text-slate-600 hover:text-blue-600 shadow-sm rounded-lg px-3 flex items-center justify-center transition-all"
              >
                {hasCopied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
              </button>
            </div>
            
            <button
              onClick={() => setNewlyGeneratedKey(null)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-xl transition-colors"
            >
              I saved my key
            </button>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto space-y-8 relative z-10">
        
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-200 pb-6">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg">
              <Activity size={24} />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Job Processing Core</h1>
              <p className="text-slate-500">Service Gateway & Orchestration Dashboard</p>
            </div>
          </div>
          <button onClick={logout} className="flex items-center gap-2 text-slate-500 hover:text-red-600 font-medium bg-white border border-slate-200 px-4 py-2 rounded-lg transition-colors">
            <LogOut size={16} /> Sign Out
          </button>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* TASK 1: API KEYS */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <div className="flex items-center gap-2">
                  <KeyRound size={20} className="text-blue-600" />
                  <h2 className="text-lg font-semibold">Identity Manager</h2>
                </div>
                <button
                  onClick={generateKey}
                  disabled={isGenerating}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {isGenerating ? "Provisioning..." : "Generate API Key"}
                </button>
              </div>
              
              <div className="p-6 space-y-4">
                {apiKeys.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
                    <Key size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No keys generated yet.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <label className="text-sm font-medium text-slate-700">Active Credentials</label>
                    <select
                      value={selectedKey}
                      onChange={(e) => setSelectedKey(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                      {apiKeys.map((k, i) => (
                        <option key={k.api_key} value={k.api_key}>
                          Key {apiKeys.length - i} : {k.api_key.substring(0, 16)}...
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* TASK 1: RATE LIMITING */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-6 border-b border-slate-100 flex items-center gap-2 bg-slate-50">
                <ShieldAlert size={20} className="text-red-500" />
                <h2 className="text-lg font-semibold">Quota Verification</h2>
              </div>
              <div className="p-6 space-y-4">
                
                {/* USAGE TRACKER GAUGE */}
                {(usage && selectedKey) && (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
                     <div className="flex justify-between items-end mb-2">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Usage tracking</span>
                        <span className="text-sm font-bold text-slate-900">{usage.request_count} / {usage.rate_limit} Req</span>
                     </div>
                     <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                        <div 
                          className={`h-2.5 rounded-full transition-all duration-500 ease-out ${usage.request_count >= usage.rate_limit ? 'bg-red-500' : 'bg-blue-600'}`} 
                          style={{ width: `${Math.min((usage.request_count / usage.rate_limit) * 100, 100)}%` }}
                        ></div>
                     </div>
                     <p className="text-xs text-slate-400 mt-2 text-right">Window Resets every {usage.window_seconds}s</p>
                  </div>
                )}

                <p className="text-sm text-slate-500">
                  Send a request to the protected resource. Valid keys are strictly limited to <span className="font-semibold text-slate-700">5 requests per minute</span>.
                </p>
                <button
                  onClick={testRateLimit}
                  disabled={!selectedKey}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <Play size={16} /> Execute Secure Fetch
                </button>
                
                {testResult && (
                  <div className={`p-4 rounded-xl border ${testResult.status === 200 ? 'bg-green-50 border-green-200 text-green-800' : testResult.status === 429 ? 'bg-red-50 border-red-200 text-red-800' : 'bg-orange-50 border-orange-200 text-orange-800'}`}>
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-bold">{testResult.status === 200 ? "200 Success" : `${testResult.status} Blocked`}</span>
                      <span className="text-xs font-mono opacity-60">{testResult.time}ms</span>
                    </div>
                    <p className="text-sm">{testResult.text}</p>
                  </div>
                )}
              </div>
            </div>
          </div>


          {/* TASK 2: BACKGROUND JOBS */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
            <div className="p-6 border-b border-slate-100 bg-slate-50">
              <div className="flex items-center gap-2 mb-4">
                <Cpu size={20} className="text-purple-600" />
                <h2 className="text-lg font-semibold">Asynchronous Job Queue</h2>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  className="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:outline-none"
                  placeholder="Task configuration..."
                />
                <button
                  onClick={submitJob}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Dispatch
                </button>
              </div>
            </div>
            
            <div className="p-6 flex-1 overflow-y-auto bg-slate-50/50 space-y-4">
              {jobs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 py-12">
                  <Box size={48} className="opacity-20 mb-4" />
                  <p>Queue is empty.</p>
                </div>
              ) : (
                jobs.map((job) => (
                  <div key={job.id} className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 relative overflow-hidden group">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium text-slate-900">{job.task}</h3>
                        <p className="text-xs font-mono text-slate-400 mt-1">{job.id}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium uppercase tracking-wide flex items-center gap-1 ${
                        job.status === 'completed' ? 'bg-green-100 text-green-700' :
                        job.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {job.status === 'in_progress' && <RefreshCw size={12} className="animate-spin" />}
                        {job.status}
                      </span>
                    </div>
                    
                    {job.status === 'completed' && job.result && (
                      <div className="mt-4 pt-3 border-t border-slate-100">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Worker Output</span>
                        <p className="text-sm font-mono bg-slate-50 p-2 rounded text-slate-700">{job.result}</p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
