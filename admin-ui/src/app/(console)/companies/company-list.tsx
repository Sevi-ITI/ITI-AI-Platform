"use client";

import { useState } from "react";

import dash from "../dashboard.module.css";

// The company cards with a search box above them (same as Apps & keys). The server builds each card and the text it
// can be found by (name, id, notes, collections); typing filters the grid at once, every word must match.

export type CompanyItem = { id: string; text: string; card: React.ReactNode };

export default function CompanyList({ items }: { items: CompanyItem[] }) {
  const [query, setQuery] = useState("");
  const words = query.trim().toLowerCase();
  const shown = items.filter((item) => words.split(/\s+/).every((w) => item.text.includes(w)));

  return (
    <>
      <label className={dash.search}>
        <span className="sr-only">Search companies</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by company, id, notes or collection…"
          autoComplete="off"
          spellCheck={false}
        />
      </label>

      {/* screen readers hear how many are shown while typing */}
      <p className="sr-only" role="status">
        {words ? `${shown.length} of ${items.length} companies shown` : ""}
      </p>

      {shown.length === 0 ? (
        <p className={dash.muted}>No company matches &quot;{query.trim()}&quot;.</p>
      ) : (
        <ul className={dash.companyGrid} aria-label="Companies">
          {shown.map((item) => (
            <li key={item.id}>{item.card}</li>
          ))}
        </ul>
      )}
    </>
  );
}
