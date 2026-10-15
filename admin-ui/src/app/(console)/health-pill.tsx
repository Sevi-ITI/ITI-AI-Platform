"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { HealthPillData } from "@/app/api/health/route";
import { formatMs, formatTime } from "@/lib/format";

import styles from "./console.module.css";
import { StatusErrorIcon, StatusOkIcon, StatusWarnIcon } from "./icons";

// The sidebar's health pill: database, Ollama and the answer queue at a glance, on every page. Asks /api/health
// every 30 s (the layout doesn't re-render on page changes, so the pill fetches by itself), skipped while the tab is
// hidden and once right away when it comes back. Details on hover; a click opens Overview.

const SECONDS = 30;

type Shown = { tone: "ok" | "warn" | "error"; text: string; detail: string } | null;

function describe(h: HealthPillData, at: string): NonNullable<Shown> {
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

export default function HealthPill() {
  const router = useRouter();
  const [shown, setShown] = useState<Shown>(null);

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
          setShown({ tone: "error", text: "Can't check", detail: `${body?.error?.message ?? "No answer"}\nChecked ${at}` });
          return;
        }
        setShown(describe((await r.json()) as HealthPillData, at));
      } catch {
        if (!stopped) setShown({ tone: "error", text: "Can't check", detail: `The console server didn't answer.\nChecked ${at}` });
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

  const Icon = shown?.tone === "ok" ? StatusOkIcon : shown?.tone === "warn" ? StatusWarnIcon : StatusErrorIcon;

  return (
    <Link
      href="/"
      className={`${styles.health} ${shown ? styles[`health_${shown.tone}`] : ""}`}
      title={shown ? `${shown.text}\n${shown.detail}` : "Checking the system…"}
    >
      {shown ? <Icon /> : <span className={styles.healthChecking} aria-hidden="true" />}
      <span className={styles.label}>{shown ? shown.text : "Checking…"}</span>
    </Link>
  );
}
