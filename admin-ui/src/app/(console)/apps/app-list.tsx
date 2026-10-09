"use client";

import { useState } from "react";

import dash from "../dashboard.module.css";

// The app cards with a search box above them. The server builds each card and the text it can be found by
// (app id, name, owner, company, key ids); typing filters both groups at once. "Disconnected apps" (no active
// keys) is folded away, and opens by itself when the search finds something in it.

export type AppItem = { id: string; text: string; card: React.ReactNode };

export default function AppList({ active, disconnected }: { active: AppItem[]; disconnected: AppItem[] }) {
  const [query, setQuery] = useState("");
  const words = query.trim().toLowerCase();
  const matches = (item: AppItem) => words.split(/\s+/).every((w) => item.text.includes(w));
  const shownActive = active.filter(matches);
  const shownDisconnected = disconnected.filter(matches);
  const nothing = words && shownActive.length === 0 && shownDisconnected.length === 0;

  return (
    <>
      <label className={dash.search}>
        <span className="sr-only">Search apps and keys</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by app, name, owner, company or key id…"
          autoComplete="off"
          spellCheck={false}
        />
      </label>

      {nothing && <p className={dash.muted}>No app or key matches &quot;{query.trim()}&quot;.</p>}
      {shownActive.map((item) => (
        <div key={item.id}>{item.card}</div>
      ))}

      {disconnected.length > 0 && (!words || shownDisconnected.length > 0) && (
        // the key re-opens the group when a search finds something in it (and closes it when cleared)
        <details key={words ? "found" : "all"} className={dash.disconnected} open={Boolean(words)}>
          <summary>
            Disconnected apps ({words ? `${shownDisconnected.length} of ${disconnected.length}` : disconnected.length})
            <span className={dash.muted}> · no active keys; kept as history</span>
          </summary>
          <div className={dash.disconnectedList}>
            {shownDisconnected.map((item) => (
              <div key={item.id}>{item.card}</div>
            ))}
          </div>
        </details>
      )}
    </>
  );
}
