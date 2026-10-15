import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import { clearSession } from "@/lib/session/cookie";

// GET /api/health: the sidebar's health pill asks here every 30 s (the browser never calls FastAPI). Only the few
// fields the pill shows go back; the full report stays on Overview. Behind proxy.ts like every console page.

export type HealthPillData = {
  status: "ok" | "degraded";
  database: { ok: boolean; latency_ms: number | null };
  ollama: { ok: boolean; latency_ms: number | null };
  queue: { running: number; limit: number; waiting: number };
};

export async function GET() {
  const health = await callApi((api) => api.GET("/v1/admin/health"));
  if (!health.ok) {
    if (health.error.status === 401) await clearSession();
    // status 0 = FastAPI not reachable: 502 (a Response can't carry 0)
    return Response.json(
      { error: { message: displayMessage(health.error) } },
      { status: health.error.status || 502 },
    );
  }

  const h = health.data;
  const data: HealthPillData = {
    status: h.status,
    database: { ok: h.database.ok, latency_ms: h.database.latency_ms },
    ollama: { ok: h.ollama.ok, latency_ms: h.ollama.latency_ms },
    queue: { running: h.llm_slots.running, limit: h.llm_slots.limit, waiting: h.llm_slots.waiting },
  };
  return Response.json(data, { headers: { "Cache-Control": "no-store" } });
}
