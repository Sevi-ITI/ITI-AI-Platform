"use client";

import { useEffect, useState } from "react";

import dash from "./dashboard.module.css";

// Toasts: a short notice in the corner after a change ("✓ Key revoked", "✕ Upload failed: …").
// Call toast("ok", "…") from any client component; <Toaster /> (in the console layout) shows them.
// Successes fade after 5 s, failures after 9 s; each can be closed. Screen readers hear them (aria-live).

type Kind = "ok" | "error";
type Item = { id: number; kind: Kind; text: string };

let nextId = 1;
const listeners = new Set<(items: Item[]) => void>();
let items: Item[] = [];

function emit() {
  for (const l of listeners) l(items);
}

function dismiss(id: number) {
  items = items.filter((t) => t.id !== id);
  emit();
}

export function toast(kind: Kind, text: string) {
  const id = nextId++;
  items = [...items.slice(-3), { id, kind, text }]; // at most 4 on screen
  emit();
  setTimeout(() => dismiss(id), kind === "ok" ? 5000 : 9000);
}

export default function Toaster() {
  const [shown, setShown] = useState<Item[]>([]);

  useEffect(() => {
    listeners.add(setShown);
    return () => {
      listeners.delete(setShown);
    };
  }, []);

  return (
    <div className={dash.toasts} role="status" aria-live="polite">
      {shown.map((t) => (
        <div key={t.id} className={t.kind === "ok" ? dash.toastOk : dash.toastError}>
          <span>
            {t.kind === "ok" ? "✓" : "✕"} {t.text}
          </span>
          <button type="button" onClick={() => dismiss(t.id)} aria-label="Close notice">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
