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

function SearchPanel() {
  return (
    <div className="content-area">
      <section className="panel-hero panel-hero-tight">
        <p className="panel-eyebrow">Corpus search</p>
        <h2>Search across the case library.</h2>
        <p>
          This area is reserved for semantic and metadata search once the search
          endpoint is connected to the interface.
        </p>
      </section>
      <div className="placeholder-state">
        <div className="ph-icon">01</div>
        <h3>Case Search</h3>
        <p>Full-text and semantic search across the legal corpus via <code>POST /api/search</code>.</p>
      </div>
    </div>
  );
}

function SimilarPanel() {
  return (
    <div className="content-area">
      <section className="panel-hero panel-hero-tight">
        <p className="panel-eyebrow">Related matters</p>
        <h2>Trace neighboring precedents.</h2>
        <p>
          Use this panel to pivot from one matter to comparable cases and supporting
          authorities once the similarity endpoint is wired in.
        </p>
      </section>
      <div className="placeholder-state">
        <div className="ph-icon">02</div>
        <h3>Similar Cases</h3>
        <p>Find nearby precedents from a case ID or text snippet via <code>POST /api/similar-cases</code>.</p>
      </div>
    </div>
  );
}
