import "server-only";

import { cache } from "react";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";

import styles from "./dashboard.module.css";
import { GpuAndModels, Problem } from "./widgets";

// GET /v1/admin/health is the slow call (~0.7 s: FastAPI runs nvidia-smi). The cards that need it are
// streamed: the page shows at once, these fill in when it answers. One call per page load, shared.
export const currentHealth = cache(() => callApi((api) => api.GET("/v1/admin/health")));

export async function GpuCard({ title }: { title: string }) {
  const health = await currentHealth();
  endSessionOn401(health);

  return (
    <section className={styles.card} aria-labelledby="gpu">
      <h2 id="gpu">{title}</h2>
      {health.ok ? <GpuAndModels health={health.data} /> : <Problem message={displayMessage(health.error)} />}
    </section>
  );
}

/** Placeholder with roughly the card's final height, so nothing jumps when it fills in. */
export function CardLoading({ title, height }: { title: string; height: string }) {
  return (
    <section className={styles.card} aria-busy="true">
      <h2>{title}</h2>
      <p className={styles.muted} style={{ minHeight: height }}>
        Checking the system…
      </p>
    </section>
  );
}
