"use client";

// Apps & keys, game-ui's own list (not a copy of admin-ui since the declutter, 2026-10-27): the app cards in labelled
// groups (the console, In use, Idle or not used yet; Disconnected folded) with a search box above them. The server
// builds each card and the text it can be found by (app id, name, owner, company, key ids); typing filters every
// group at once, and "Disconnected" opens by itself when the search finds something in it.
import { useState } from "react";

import dash from "../kit/dashboard.module.css";
import { SearchingContext } from "./app-details";
import css from "./apps.module.css";

export type AppGroup = "console" | "in-use" | "idle" | "disconnected";

export type AppItem = { id: string; text: string; group: AppGroup; card: React.ReactNode };

const GROUPS: { id: Exclude<AppGroup, "disconnected">; title: string }[] = [
  { id: "console", title: "The console" },
  { id: "in-use", title: "In use" },
  { id: "idle", title: "Idle or not used yet" },
];

export default function AppList({ items, initialQuery = "" }: { items: AppItem[]; initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const words = query.trim().toLowerCase();
  const matches = (item: AppItem) => words.split(/\s+/).every((w) => item.text.includes(w));
  const shown = items.filter(matches);
  const disconnected = items.filter((it) => it.group === "disconnected");
  const shownDisconnected = shown.filter((it) => it.group === "disconnected");

  return (
    // while the search has text, every shown card is open (AppDetails reads this)
    <SearchingContext value={Boolean(words)}>
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

      {words && shown.length === 0 && <p className={dash.muted}>No app or key matches &quot;{query.trim()}&quot;.</p>}

      {GROUPS.map((g) => {
        const list = shown.filter((it) => it.group === g.id);
        return (
          list.length > 0 && (
            <section key={g.id} className={css.group} aria-label={g.title}>
              <h2 className={css.groupTitle}>
                {g.title} <span className={css.groupCount}>{list.length}</span>
              </h2>
              {list.map((item) => (
                <div key={item.id}>{item.card}</div>
              ))}
            </section>
          )
        );
      })}

      {disconnected.length > 0 && (!words || shownDisconnected.length > 0) && (
        // the key re-opens the group when a search finds something in it (and closes it when cleared)
        <details key={words ? "found" : "all"} className={dash.disconnected} open={Boolean(words)}>
          <summary>
            Disconnected ({words ? `${shownDisconnected.length} of ${disconnected.length}` : disconnected.length})
            <span className={dash.muted}> · no active keys; kept as history</span>
          </summary>
          <div className={dash.disconnectedList}>
            {shownDisconnected.map((item) => (
              <div key={item.id}>{item.card}</div>
            ))}
          </div>
        </details>
      )}
    </SearchingContext>
  );
}
