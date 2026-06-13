"use client";
import { useState, useEffect } from "react";
import type { Panel } from "@/app/page";

const NAV_ITEMS: { id: Panel; icon: string; label: string }[] = [
  { id: "query",   icon: "search",  label: "Legal Query"   },
  { id: "search",  icon: "file",    label: "Case Search"   },
  { id: "similar", icon: "link",    label: "Similar Cases" },
  { id: "agents",  icon: "grid",    label: "Agents"        },
];

function Icon({ name }: { name: string }) {
  const icons: Record<string, JSX.Element> = {
    search: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>,
    file:   <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
    link:   <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>,
    grid:   <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
    shield: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c8c4b8" strokeWidth="1.8"><path d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.25C17.25 22.15 21 17.25 21 12V7z"/><path d="M9 12l2 2 4-4" stroke="#c8c4b8"/></svg>,
  };
  return icons[name] ?? null;
}

export default function Sidebar({ activePanel, onNavigate }: { activePanel: Panel; onNavigate: (p: Panel) => void }) {
  const [mounted, setMounted] = useState(false);
  const [provider, setProvider] = useState("simulation");
  const [geminiKey, setGeminiKey] = useState("");
  const [ollamaStatus, setOllamaStatus] = useState<"idle" | "checking" | "connected" | "disconnected">("idle");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaError, setOllamaError] = useState<string | null>(null);

  const checkOllamaConnection = async () => {
    setOllamaStatus("checking");
    setOllamaError(null);
    try {
      const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiHost}/api/check-ollama`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.status === "connected") {
        setOllamaStatus("connected");
        setOllamaModels(data.models || []);
      } else {
        setOllamaStatus("disconnected");
        setOllamaError(data.error || "Could not reach Ollama");
      }
    } catch (err: any) {
      setOllamaStatus("disconnected");
      setOllamaError(err.message || "Failed to contact backend verification api");
    }
  };

  useEffect(() => {
    setMounted(true);
    const savedProvider = localStorage.getItem("lexverify_provider") || "simulation";
    setProvider(savedProvider);
    setGeminiKey(localStorage.getItem("lexverify_gemini_key") || "");
    
    // Auto-check Ollama if provider is ollama on load
    if (savedProvider === "ollama") {
      // Small timeout to let mount complete
      setTimeout(checkOllamaConnection, 100);
    }
  }, []);

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const p = e.target.value;
    setProvider(p);
    localStorage.setItem("lexverify_provider", p);
    if (p === "ollama") {
      checkOllamaConnection();
    }
  };

  const handleKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const k = e.target.value;
    setGeminiKey(k);
    localStorage.setItem("lexverify_gemini_key", k);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon"><Icon name="shield" /></div>
        <div>
          <div className="logo-name">LexVerify</div>
          <div className="logo-sub">Legal AI Agent</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Research</div>
        {NAV_ITEMS.slice(0, 3).map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activePanel === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            <Icon name={item.icon} />
            {item.label}
          </button>
        ))}
        <div className="nav-section-label" style={{ marginTop: "1.25rem" }}>System</div>
        {NAV_ITEMS.slice(3).map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activePanel === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            <Icon name={item.icon} />
            {item.label}
          </button>
        ))}

        <div className="nav-section-label" style={{ marginTop: "1.25rem" }}>Model Config</div>
        {mounted && (
          <div className="settings-section">
            <div className="settings-input-group">
              <label className="settings-input-label">Provider</label>
              <select className="settings-select" value={provider} onChange={handleProviderChange}>
                <option value="simulation">Simulation (Offline)</option>
                <option value="gemini">Gemini (Cloud)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            
            {provider === "gemini" && (
              <div className="settings-input-group">
                <label className="settings-input-label">Gemini API Key</label>
                <input
                  type="password"
                  className="settings-input"
                  placeholder="AIzaSy..."
                  value={geminiKey}
                  onChange={handleKeyChange}
                />
              </div>
            )}

            {provider === "ollama" && (
              <>
                <div className="status-indicator">
                  <div className={`status-dot ${ollamaStatus === "checking" ? "checking" : ollamaStatus === "connected" ? "connected" : "disconnected"}`} />
                  <span className="status-text">
                    {ollamaStatus === "checking"
                      ? "Checking connection..."
                      : ollamaStatus === "connected"
                      ? "Connected"
                      : "Offline"}
                </div>
                {ollamaStatus === "connected" && ollamaModels.length > 0 && (
                  <div className="settings-input-group" style={{ marginTop: "0.5rem" }}>
                    <label className="settings-input-label">Ollama Model</label>
                    <select 
                      className="settings-select"
                      onChange={(e) => localStorage.setItem("lexverify_ollama_model", e.target.value)}
                      defaultValue={localStorage.getItem("lexverify_ollama_model") || (ollamaModels.includes("lexverify-legal") || ollamaModels.includes("lexverify-legal:latest") ? "lexverify-legal" : ollamaModels[0])}
                    >
                      {ollamaModels.map(m => (
                        <option key={m} value={m}>
                          {m === "lexverify-legal" || m === "lexverify-legal:latest" ? "lexverify-legal (Recommended)" : m}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {ollamaStatus === "disconnected" && ollamaError && (
                  <div className="available-models" style={{ color: "#8a4747" }}>
                    {ollamaError}
                  </div>
                )}
                <button
                  type="button"
                  className="connect-btn"
                  onClick={checkOllamaConnection}
                  disabled={ollamaStatus === "checking"}
                >
                  {ollamaStatus === "checking" ? "Verifying..." : "Connect / Retry"}
                </button>

                <div className="ollama-guide">
                  <span className="ollama-guide-title">Local Setup steps</span>
                  <ol className="ollama-guide-steps">
                    <li>
                      Download and install from{" "}
                      <a
                        href="https://ollama.com"
                        target="_blank"
                        rel="noreferrer"
                        style={{ textDecoration: "underline", color: "var(--accent-deep)", fontWeight: 700 }}
                      >
                        ollama.com
                      </a>
                    </li>
                    <li>
                      Launch the Ollama desktop app.
                    </li>
                    <li>
                      Pull models via your terminal:
                      <code className="ollama-guide-code">
                        ollama run llama3{"\n"}
                        ollama pull nomic-embed-text
                      </code>
                    </li>
                    <li>Click <strong>Connect / Retry</strong> above to verify.</li>
                  </ol>
                </div>
              </>
            )}
          </div>
        )}
      </nav>

      <div className="sidebar-stats">
        {[
          { label: "Hallucination rate", value: "0%", ok: true },
          { label: "Pipeline", value: "3-Agent RAG" },
          { label: "LLM temperature", value: "0.0" },
        ].map((s) => (
          <div key={s.label} className="stat-pill">
            <span className="stat-pill-label">{s.label}</span>
            <span className="stat-pill-value" style={s.ok ? { color: "#0f6e56" } : undefined}>
              {s.value}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}
