"use client";

import { createContext, useContext } from "react";

import dash from "../dashboard.module.css";

// One app card as a fold (native <details>: keyboard and screen readers work without extra code). The summary is a
// one-line overview; the body holds the actions and the keys. It starts open when the app was used recently, and
// every card opens while the search box has text (AppList provides SearchingContext), so a match is never hidden.

export const SearchingContext = createContext(false);

export default function AppDetails({
  defaultOpen,
  summary,
  children,
}: {
  defaultOpen: boolean;
  summary: React.ReactNode;
  children: React.ReactNode;
}) {
  const searching = useContext(SearchingContext);
  return (
    // the key resets the open state when a search starts or is cleared
    <details key={searching ? "search" : "all"} className={dash.appCard} open={searching || defaultOpen}>
      <summary>{summary}</summary>
      <div className={dash.appBody}>{children}</div>
    </details>
  );
}
