"use client";

import { useState } from "react";
import type { QueryResponse } from "@/types/api";
import CitationCard from "./CitationCard";
import {
  ValidationPanel,
  AgentTrace,
  PipelineTracker,
  ConfidenceRing,
} from "./index";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAMPLE_QUERIES = [
  "Anticipatory bail under Section 438 CrPC",
  "Maneka Gandhi expansion of Article 21",
  "Miranda rights in custodial interrogation",
  "Arrest without warrant — Section 41A CrPC",
];

const JURISDICTIONS = [
  { value: "all", label: "All jurisdictions" },
  { value: "india", label: "India" },
  { value: "usa", label: "USA" },
  { value: "uk", label: "UK" },
];

type Tab = "answer" | "citations" | "validation" | "trace";

export default function QueryInterface() {
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState("all");
  const [loading, setLoading] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<number>(0);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("answer");
  const [error, setError] = useState<string | null>(null);

  async function runQuery() {
    const q = query.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setPipelineStage(1);

    const stageDelay = (ms: number) =>
      new Promise<void>((r) => setTimeout(r, ms));

    try {
      // Animate pipeline stages while waiting
      const animTask = (async () => {
        await stageDelay(600);
        setPipelineStage(2);
        await stageDelay(800);
        setPipelineStage(3);
        await stageDelay(700);
      })();

      const res = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, jurisdiction, top_k: 5 }),
      });

      await animTask;
      setPipelineStage(4);
      await stageDelay(400);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data: QueryResponse = await res.json();
      setResult(data);
      setActiveTab("answer");
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
      setPipelineStage(0);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") runQuery();
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "answer", label: "Answer" },
    { key: "citations", label: `Citations${result ? ` (${result.citations.length})` : ""}` },
    { key: "validation", label: "Validation" },
    { key: "trace", label: "Agent trace" },
  ];

  return (
    <div className="content-area">
      <section className="query-hero">
        <div className="query-hero-copy">
          <p className="panel-eyebrow">Verification-first workspace</p>
          <h1 className="query-hero-title">Verification-First Legal AI Agent.</h1>
          <p className="query-hero-text">
            Ask a legal question, narrow the jurisdiction, and get an answer only if the
            system can support it with retrieved authority, exact citation details, and a
            validator-approved confidence score.
          </p>
        </div>
        <div className="hero-metrics">
          <div className="hero-metric">
            <span className="hero-metric-value">3</span>
            <span className="hero-metric-label">sequential agents</span>
          </div>
          <div className="hero-metric">
            <span className="hero-metric-value">0%</span>
            <span className="hero-metric-label">hallucination target</span>
          </div>
          <div className="hero-metric">
            <span className="hero-metric-value">100%</span>
            <span className="hero-metric-label">citation-backed answers only</span>
          </div>
        </div>
      </section>

      <div className="query-box">
        <div className="query-box-head">
          <div>
            <label className="query-label">Legal question</label>
            <p className="query-supporting">Compose a research prompt the system can defend with cases, courts, years, and exact references.</p>
          </div>
          <span className="query-status">{loading ? "Review in progress" : "Ready for intake"}</span>
        </div>
        <div className="query-row">
          <input
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. What are the grounds for anticipatory bail under Indian law?"
            disabled={loading}
          />
          <select
            className="jx-select"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            disabled={loading}
          >
            {JURISDICTIONS.map((j) => (
              <option key={j.value} value={j.value}>{j.label}</option>
            ))}
          </select>
          <button
            className="submit-btn"
            onClick={runQuery}
            disabled={loading || !query.trim()}
          >
            {loading ? "Analyzing..." : "Generate brief"}
          </button>
        </div>
        <div className="sample-queries">
          <span className="sample-label">Suggested prompts</span>
          {SAMPLE_QUERIES.map((sq) => (
            <button
              key={sq}
              className="sample-q"
              onClick={() => setQuery(sq)}
              disabled={loading}
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline tracker */}
      {(loading || pipelineStage > 0) && (
        <PipelineTracker currentStage={pipelineStage} />
      )}

      {/* Error */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">✕</span>
          <span>{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="answer-card">
          <div className="answer-header">
            <div className="answer-header-left">
              <p className="answer-query">"{result.query}"</p>
              <div className="answer-badges">
                <span className={`badge ${result.validation.citation_verified ? "badge-ok" : "badge-err"}`}>
                  {result.validation.citation_verified ? "✓ Citations verified" : "✗ Unverified"}
                </span>
                <span className={`badge badge-conf-${result.validation.confidence_label.toLowerCase()}`}>
                  {result.validation.confidence_label} confidence
                </span>
                <span className="badge badge-neutral">
                  {result.citations.length} citation{result.citations.length !== 1 ? "s" : ""}
                </span>
                <span className="badge badge-neutral">
                  {result.latency_ms.toFixed(0)} ms
                </span>
              </div>
            </div>
            <ConfidenceRing
              score={result.validation.confidence_score}
              label={result.validation.confidence_label}
            />
          </div>

          {/* Tabs */}
          <div className="tab-bar">
            {tabs.map((t) => (
              <button
                key={t.key}
                className={`tab ${activeTab === t.key ? "active" : ""}`}
                onClick={() => setActiveTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === "answer" && (
            <div className="tab-content">
              {result.fallback ? (
                <div className="fallback-box">
                  <div className="fallback-icon">⚠</div>
                  <div>
                    <strong>No verified legal information found.</strong>
                    <p>
                      The system could not locate any relevant, verified case law or statutory
                      provisions to answer this query with citations. Please consult a licensed
                      legal professional.
                    </p>
                  </div>
                </div>
              ) : (
                <div
                  className="answer-body"
                  dangerouslySetInnerHTML={{ __html: formatAnswer(result.answer, result.citations) }}
                />
              )}
            </div>
          )}

          {activeTab === "citations" && (
            <div className="tab-content">
              {result.citations.length === 0 ? (
                <p className="empty-tab">No verified citations available.</p>
              ) : (
                result.citations.map((c) => <CitationCard key={c.id} citation={c} />)
              )}
            </div>
          )}

          {activeTab === "validation" && (
            <div className="tab-content">
              <ValidationPanel validation={result.validation} />
            </div>
          )}

          {activeTab === "trace" && (
            <div className="tab-content">
              <AgentTrace trace={result.agent_trace || []} />
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">LV</div>
          <p className="panel-eyebrow">Briefing room</p>
          <h3>Accuracy &gt; Fluency. Proof &gt; Confidence.</h3>
          <p>
            Every answer must be backed by retrieved legal material from Indian Kanoon or
            CourtListener. If the system cannot verify the record, it returns
            &quot;No verified legal information found&quot; instead of improvising.
          </p>
          <div className="empty-feature-grid">
            <div className="empty-feature">
              <strong>Retrieve</strong>
              <span>Embeds the query and retrieves the strongest legal authorities first.</span>
            </div>
            <div className="empty-feature">
              <strong>Validate</strong>
              <span>Checks citations, consistency, confidence, and reference completeness before release.</span>
            </div>
            <div className="empty-feature">
              <strong>Fallback honestly</strong>
              <span>Returns a strict no-answer response when verified support is insufficient.</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatAnswer(answer: string, citations: any[]): string {
  let html = answer
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  citations.forEach((c) => {
    const shortName = c.case_name.includes(" v. ")
      ? c.case_name.split(" v. ")[0]
      : c.case_name.slice(0, 25);
    html = html.replace(
      new RegExp(`\\[CITE:${c.id}\\]`, "g"),
      `<a class="cite-inline" href="${c.url}" target="_blank" rel="noopener">[${shortName} ${c.year}]</a>`
    );
  });

  // Wrap paragraphs
  html = html
    .split(/\n\n+/)
    .map((p) => `<p>${p.replace(/\n/g, "<br/>")}</p>`)
    .join("");

  return html;
}
