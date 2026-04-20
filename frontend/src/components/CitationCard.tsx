"use client";
import type { Citation } from "@/types/api";

export default function CitationCard({ citation: c }: { citation: Citation }) {
  const pct = Math.round(c.relevance_score * 100);
  const sourceLabel = c.source === "indian_kanoon" ? "Indian Kanoon" : "CourtListener";

  return (
    <div className="citation-card" onClick={() => c.url && window.open(c.url, "_blank")}>
      <div className="citation-top">
        <div>
          <p className="citation-name">{c.case_name}</p>
          <p className="citation-meta">
            {c.court} &middot; {c.year} &middot; {sourceLabel}
          </p>
        </div>
        <div className="relevance-wrap">
          <div className="relevance-bar">
            <div className="relevance-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="relevance-num">{pct}%</span>
        </div>
      </div>
      <blockquote className="citation-para">{c.paragraph}</blockquote>
      {c.url && (
        <a
          className="citation-link"
          href={c.url}
          target="_blank"
          rel="noopener"
          onClick={(e) => e.stopPropagation()}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
          View original document
        </a>
      )}
    </div>
  );
}
