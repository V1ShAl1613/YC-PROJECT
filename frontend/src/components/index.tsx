// ─── ValidationPanel ─────────────────────────────────────────────────────────
"use client";
import type { ValidationResult } from "@/types/api";

export function ValidationPanel({ validation: v }: { validation: ValidationResult }) {
  const cells = [
    { label: "Citation verified", value: v.citation_verified ? "Pass" : "Fail", ok: v.citation_verified },
    { label: "Cross-consistent",  value: v.cross_consistent  ? "Pass" : "Fail", ok: v.cross_consistent  },
    { label: "Confidence score",  value: `${Math.round(v.confidence_score * 100)}%`, ok: v.confidence_score >= 0.7 },
    { label: "Confidence label",  value: v.confidence_label, ok: v.confidence_label === "HIGH" },
  ];
  return (
    <div>
      <div className="val-grid">
        {cells.map((c) => (
          <div key={c.label} className="val-cell">
            <p className="val-label">{c.label}</p>
            <p className="val-value" style={{ color: c.ok ? "#0f6e56" : "#8b2020" }}>{c.value}</p>
          </div>
        ))}
      </div>
      {v.rejection_reasons.length > 0 && (
        <div className="rejection-list">
          <p className="rejection-title">Rejection reasons</p>
          {v.rejection_reasons.map((r, i) => (
            <p key={i} className="rejection-item">· {r}</p>
          ))}
        </div>
      )}
    </div>
  );
}


// ─── AgentTrace ──────────────────────────────────────────────────────────────
export function AgentTrace({ trace }: { trace: string[] }) {
  function lineClass(line: string) {
    if (line.includes("VALIDATED") || (line.includes("result:") && !line.includes("NO "))) return "trace-ok";
    if (line.includes("NO DOCUMENTS") || line.includes("FAILED") || line.includes("ERROR")) return "trace-err";
    if (line.includes("result:")) return "trace-warn";
    return "";
  }
  return (
    <div className="trace-box">
      {trace.length === 0 ? (
        <span className="trace-empty">No trace available.</span>
      ) : (
        trace.map((line, i) => (
          <div key={i} className="trace-line">
            <span className="trace-num">{String(i + 1).padStart(2, "0")}</span>
            <span className={lineClass(line)}>{line}</span>
          </div>
        ))
      )}
    </div>
  );
}


// ─── PipelineTracker ─────────────────────────────────────────────────────────
export function PipelineTracker({ currentStage }: { currentStage: number }) {
  const stages = [
    { num: 1, label: "Research\nAgent" },
    { num: 2, label: "Legal Analyst\nAgent" },
    { num: 3, label: "Validator\nAgent" },
    { num: 4, label: "Verified\nAnswer" },
  ];
  return (
    <div className="pipeline-track">
      <p className="pipeline-title">Agent pipeline</p>
      <div className="pipeline-steps">
        {stages.map((s, i) => {
          const isDone   = s.num < currentStage;
          const isActive = s.num === currentStage;
          return (
            <div key={s.num} className={`pipe-node ${isDone ? "done" : ""} ${isActive ? "active" : ""}`}>
              {i < stages.length - 1 && <div className={`pipe-connector ${isDone ? "done" : ""}`} />}
              <div className="pipe-circle">{isDone ? "✓" : s.num}</div>
              <p className="pipe-label">{s.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ─── ConfidenceRing ──────────────────────────────────────────────────────────
export function ConfidenceRing({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score * 100);
  const color = label === "HIGH" ? "#0f6e56" : label === "MEDIUM" ? "#85500b" : "#8b2020";
  const r = 16;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  return (
    <div className="conf-ring-wrap">
      <svg width="52" height="52" viewBox="0 0 52 52">
        <circle cx="26" cy="26" r={r} fill="none" stroke="#e5e3dc" strokeWidth="4" />
        <circle
          cx="26" cy="26" r={r} fill="none"
          stroke={color} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          transform="rotate(-90 26 26)"
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x="26" y="30" textAnchor="middle" fontSize="11" fontWeight="500" fill={color}>
          {pct}%
        </text>
      </svg>
      <div>
        <p className="conf-label-top" style={{ color }}>{label}</p>
        <p className="conf-label-sub">confidence</p>
      </div>
    </div>
  );
}


// ─── Topbar ──────────────────────────────────────────────────────────────────
import type { Panel } from "@/app/page";
import { useEffect, useState } from "react";

const TITLES: Record<Panel, string> = {
  query:   "Verification-First Legal AI",
  search:  "Case Search",
  similar: "Similar Cases",
  agents:  "Agent Architecture",
};

export function Topbar({ activePanel }: { activePanel: Panel }) {
  const [modelInfo, setModelInfo] = useState<string>("Loading model status...");

  useEffect(() => {
    const fetchModelStatus = async () => {
      try {
        const apiHost = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiHost}/api/model-status`);
        if (res.ok) {
          const data = await res.json();
          if (data.provider === "ollama") {
            setModelInfo(`Local LLM: ${data.llm_model} ${data.status === "loaded" ? "🟢" : "🔴"}`);
          } else if (data.provider === "gemini") {
            setModelInfo(`Cloud: ${data.llm_model}`);
          } else {
            setModelInfo("Simulation Mode (Offline)");
          }
        }
      } catch (e) {
        setModelInfo("Model status unavailable");
      }
    };
    fetchModelStatus();
    const interval = setInterval(fetchModelStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="topbar">
      <div>
        <p className="topbar-title">{TITLES[activePanel]}</p>
        <p className="topbar-meta">Production-grade legal intelligence · Citations required · Trust gated by verification</p>
      </div>
      <div style={{ display: "flex", gap: "10px" }}>
        <span className="badge" style={{ fontSize: "11px", background: "#f0f0f0", color: "#333", border: "1px solid #ddd" }}>
          {modelInfo}
        </span>
        <span className="badge badge-ok" style={{ fontSize: "11px" }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "#0f6e56", marginRight: 5 }} />
          Zero hallucination
        </span>
      </div>
    </header>
  );
}
