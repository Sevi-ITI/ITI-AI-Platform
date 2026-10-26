"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { FullHealth, HealthPillData } from "@/app/api/health/route";
import { formatMs, formatTime } from "@/lib/format";

// The HQ's health, for the roof beacon and the top bar's pill: asks /api/health every 30 s (skipped while the tab is
// hidden, once right away when it comes back). Same rules as admin-ui's health pill (health-pill.tsx).

const SECONDS = 30;

export type HealthTone = "ok" | "warn" | "error";
export type Health = { tone: HealthTone; text: string; detail: string } | null; // null = not checked yet

function describe(h: FullHealth, at: string): NonNullable<Health> {
  const down = [!h.database.ok && "database", !h.ollama.ok && "Ollama"].filter(Boolean).join(" and ");
  const detail = [
    `Database: ${h.database.ok ? `OK, ${formatMs(h.database.latency_ms)}` : "not reachable"}`,
    `Ollama: ${h.ollama.ok ? `OK, ${formatMs(h.ollama.latency_ms)}` : "not reachable"}`,
    `Answer queue: ${h.queue.running} of ${h.queue.limit} running, ${h.queue.waiting} waiting`,
    `Checked ${at}`,
  ].join("\n");

  if (h.status !== "ok") return { tone: "error", text: down ? `Down: ${down}` : "Degraded", detail };
  if (h.queue.waiting > 0) return { tone: "warn", text: `Busy: ${h.queue.waiting} waiting`, detail };
  return { tone: "ok", text: "All systems OK", detail };
}

export function useHealth(): Health {
  const router = useRouter();
  const [health, setHealth] = useState<Health>(null);

  useEffect(() => {
    let stopped = false;

    async function check() {
      const at = formatTime(new Date());
      try {
        const r = await fetch("/api/health", { cache: "no-store" });
        if (r.status === 401) {
          router.push("/login"); // the route already cleared the session cookie
          return;
        }
        if (stopped) return;
        if (!r.ok) {
          const body = (await r.json().catch(() => null)) as { error?: { message?: string } } | null;
          setHealth({ tone: "error", text: "Can't check", detail: `${body?.error?.message ?? "No answer"}\nChecked ${at}` });
          return;
        }
        const data = (await r.json()) as HealthPillData;
        setHealth(
          "simple" in data
            ? data.ok
              ? { tone: "ok", text: "Assistant available", detail: `Checked ${at}` }
              : { tone: "error", text: "Assistant unavailable", detail: `Try again in a minute.\nChecked ${at}` }
            : describe(data, at),
        );
      } catch {
        if (!stopped) setHealth({ tone: "error", text: "Can't check", detail: `The HQ server didn't answer.\nChecked ${at}` });
      }
    }

    void check();
    const timer = setInterval(() => {
      if (!document.hidden) void check();
    }, SECONDS * 1000);
    const onVisible = () => {
      if (!document.hidden) void check();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      stopped = true;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [router]);

  return health;
}
