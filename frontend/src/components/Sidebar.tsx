// ─── Sidebar ─────────────────────────────────────────────────────────────────
"use client";
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
