"use client";

import { useState } from "react";
import QueryInterface from "@/components/QueryInterface";
import Sidebar from "@/components/Sidebar";
import { Topbar } from "@/components";

export type Panel = "query" | "search" | "similar" | "agents";

export default function Home() {
  const [activePanel, setActivePanel] = useState<Panel>("query");

  return (
    <div className="app-shell">
      <Sidebar activePanel={activePanel} onNavigate={setActivePanel} />
      <div className="main-area">
        <Topbar activePanel={activePanel} />
        {activePanel === "query" && <QueryInterface />}
        {activePanel === "agents" && <AgentsPanel />}
        {activePanel === "search" && <SearchPanel />}
        {activePanel === "similar" && <SimilarPanel />}
      </div>
    </div>
  );
}

function AgentsPanel() {
  const agents = [
    {
      num: "01",
      name: "Research Agent",
      color: "#7d5c2f",
      bg: "#f0e6cd",
      desc: "Converts the user query into vector search signals, retrieves the strongest matches, and enriches each hit with structured court metadata before it moves forward.",
      tags: ["FAISS", "Embeddings", "Metadata"],
      note: "Precision starts at retrieval quality.",
    },
    {
      num: "02",
      name: "Legal Analyst Agent",
      color: "#20535f",
      bg: "#d6edf1",
      desc: "Synthesizes only from the retrieved record set, writing an answer with citation markers attached to every substantive legal claim.",
      tags: ["GPT-4o", "JSON mode", "Context only"],
      note: "No freehand reasoning outside the dossier.",
    },
    {
      num: "03",
      name: "Validator Agent",
      color: "#7a2f2f",
      bg: "#f6dede",
      desc: "Checks citation legitimacy, document completeness, contradiction risk, and confidence score before any response is allowed to leave the system.",
      tags: ["Verification", "Consistency", "Scoring"],
      note: "Critical gate that blocks unverifiable output.",
    },
  ];

  return (
    <div className="content-area">
      <section className="panel-hero panel-hero-tight">
        <p className="panel-eyebrow">System design</p>
        <h2>Production-grade legal intelligence, built around verification.</h2>
        <p>
          This is not a generic chatbot. It is a verification-first legal AI agent:
          research retrieves, analysis drafts only from evidence, and validation decides
          whether anything is safe enough to return.
        </p>
      </section>
      <div className="agents-grid">
        {agents.map((a) => (
          <div key={a.num} className="agent-card">
            <div className="agent-num" style={{ color: a.color }}>
              {a.num}
            </div>
            <h3 className="agent-name">{a.name}</h3>
            <p className="agent-desc">{a.desc}</p>
            <div className="agent-tags">
              {a.tags.map((t) => (
                <span key={t} className="agent-tag" style={{ background: a.bg, color: a.color }}>
                  {t}
                </span>
              ))}
            </div>
            {a.note && <div className="agent-note">{a.note}</div>}
          </div>
        ))}
      </div>
      <div className="pipeline-diagram">
        <div className="pipe-step">Query Intake</div>
        <div className="pipe-arrow">→</div>
        <div className="pipe-step">Top-K Retrieval</div>
        <div className="pipe-arrow">→</div>
        <div className="pipe-step">Vector Retrieval</div>
        <div className="pipe-arrow">→</div>
        <div className="pipe-step">Legal Synthesis</div>
        <div className="pipe-arrow">→</div>
        <div className="pipe-step">Validation Gate</div>
        <div className="pipe-arrow">→</div>
        <div className="pipe-step pipe-step-final">Verified Answer Only</div>
      </div>
    </div>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function SearchPanel() {
  const [query, setQuery] = useState("");
  const [court, setCourt] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [jurisdiction, setJurisdiction] = useState("all");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const filters: any = {};
      if (court) filters.court = court;
      if (yearFrom) filters.year_from = parseInt(yearFrom);
      if (yearTo) filters.year_to = parseInt(yearTo);
      if (jurisdiction !== "all") filters.jurisdiction = jurisdiction;

      const provider = localStorage.getItem("lexverify_provider") || "simulation";
      const geminiKey = localStorage.getItem("lexverify_gemini_key") || "";

      const res = await fetch(`${API_URL}/api/search`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-Model-Provider": provider,
          "X-Gemini-API-Key": geminiKey,
        },
        body: JSON.stringify({
          query,
          filters: Object.keys(filters).length ? filters : undefined,
          top_k: 10,
        }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setResults(data.results || []);
    } catch (e: any) {
      setError(e.message || "Failed to search");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="content-area">
      <section className="panel-hero panel-hero-tight">
        <p className="panel-eyebrow">Corpus search</p>
        <h2>Search across the case library.</h2>
        <p>
          Query documents semantically and filter using metadata values like court jurisdiction or publication year.
        </p>
      </section>

      <div className="query-box">
        <div className="search-row">
          <input
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search query (e.g. anticipatory bail guidelines)"
            disabled={loading}
          />
          <button
            className="submit-btn"
            onClick={handleSearch}
            disabled={loading || !query.trim()}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        <div className="filter-grid">
          <div className="filter-group">
            <label className="filter-label">Court</label>
            <input
              className="filter-input"
              value={court}
              onChange={(e) => setCourt(e.target.value)}
              placeholder="e.g. Supreme Court"
              disabled={loading}
            />
          </div>
          <div className="filter-group">
            <label className="filter-label">From Year</label>
            <input
              className="filter-input"
              type="number"
              value={yearFrom}
              onChange={(e) => setYearFrom(e.target.value)}
              placeholder="e.g. 1980"
              disabled={loading}
            />
          </div>
          <div className="filter-group">
            <label className="filter-label">To Year</label>
            <input
              className="filter-input"
              type="number"
              value={yearTo}
              onChange={(e) => setYearTo(e.target.value)}
              placeholder="e.g. 2024"
              disabled={loading}
            />
          </div>
          <div className="filter-group">
            <label className="filter-label">Jurisdiction</label>
            <select
              className="filter-select"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              disabled={loading}
            >
              <option value="all">All</option>
              <option value="india">India</option>
              <option value="usa">USA</option>
              <option value="uk">UK</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span className="error-icon">✕</span>
          <span>{error}</span>
        </div>
      )}

      {results.length > 0 ? (
        <div className="results-list">
          {results.map((res, i) => (
            <div
              key={i}
              className="citation-card"
              onClick={() => res.url && window.open(res.url, "_blank")}
            >
              <div className="citation-top">
                <div>
                  <p className="citation-name">{res.case_name || "Unknown Case Name"}</p>
                  <p className="citation-meta">
                    {res.court || "Unknown Court"} &middot; {res.year || "Unknown Year"} &middot; {res.source || "Unknown Source"}
                  </p>
                </div>
                {res.relevance_score !== undefined && (
                  <div className="relevance-wrap">
                    <span className="badge badge-ok">Score: {Math.round(res.relevance_score * 100)}%</span>
                  </div>
                )}
              </div>
              {res.summary && <blockquote className="citation-para">{res.summary}</blockquote>}
            </div>
          ))}
        </div>
      ) : (
        !loading && (
          <div className="placeholder-state">
            <div className="ph-icon">🔍</div>
            <h3>No search results</h3>
            <p>Perform a search query using the inputs above to find documents from the database.</p>
          </div>
        )
      )}
    </div>
  );
}

function SimilarPanel() {
  const [caseId, setCaseId] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleFindSimilar() {
    if (loading || (!caseId.trim() && !text.trim())) return;
    setLoading(true);
    setError(null);
    try {
      const provider = localStorage.getItem("lexverify_provider") || "simulation";
      const geminiKey = localStorage.getItem("lexverify_gemini_key") || "";

      const res = await fetch(`${API_URL}/api/similar-cases`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-Model-Provider": provider,
          "X-Gemini-API-Key": geminiKey,
        },
        body: JSON.stringify({
          case_id: caseId.trim() || undefined,
          text: text.trim() || undefined,
          top_k: 5,
        }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setResults(data.similar_cases || []);
    } catch (e: any) {
      setError(e.message || "Failed to find similar cases");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="content-area">
      <section className="panel-hero panel-hero-tight">
        <p className="panel-eyebrow">Related matters</p>
        <h2>Trace neighboring precedents.</h2>
        <p>
          Find cases that share semantic legal properties with a specific Case ID or custom text snippet.
        </p>
      </section>

      <div className="query-box">
        <div className="similar-grid">
          <div className="filter-group">
            <label className="filter-label">Case ID</label>
            <input
              className="filter-input"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="e.g. IK_2023_0001"
              disabled={loading}
            />
          </div>
          <div className="filter-group">
            <label className="filter-label">Custom text snippet</label>
            <input
              className="filter-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Or paste a key paragraph to analyze semantic similarity..."
              disabled={loading}
            />
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            className="submit-btn"
            onClick={handleFindSimilar}
            disabled={loading || (!caseId.trim() && !text.trim())}
          >
            {loading ? "Finding..." : "Find Similar"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span className="error-icon">✕</span>
          <span>{error}</span>
        </div>
      )}

      {results.length > 0 ? (
        <div className="results-list">
          {results.map((res, i) => (
            <div
              key={i}
              className="citation-card"
              onClick={() => res.url && window.open(res.url, "_blank")}
            >
              <div className="citation-top">
                <div>
                  <p className="citation-name">{res.case_name || "Unknown Case Name"}</p>
                  <p className="citation-meta">
                    {res.court || "Unknown Court"} &middot; {res.year || "Unknown Year"} &middot; {res.source || "Unknown Source"}
                  </p>
                </div>
                {res.relevance_score !== undefined && (
                  <div className="relevance-wrap">
                    <span className="badge badge-ok">Similarity: {Math.round(res.relevance_score * 100)}%</span>
                  </div>
                )}
              </div>
              {res.summary && <blockquote className="citation-para">{res.summary}</blockquote>}
            </div>
          ))}
        </div>
      ) : (
        !loading && (
          <div className="placeholder-state">
            <div className="ph-icon">🔗</div>
            <h3>No similar cases found</h3>
            <p>Enter a Case ID (e.g. <code>IK_2023_0001</code>) or enter some custom text above to view related judgments.</p>
          </div>
        )
      )}
    </div>
  );
}
