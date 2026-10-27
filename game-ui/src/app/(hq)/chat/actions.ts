"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";

// Small server calls for the upload dialog. FastAPI decides who may do what; these only pass the
// person's session along and return something the browser can show.

export type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string; status: number };

// companyId null = Global (any company's key may be given it)
export async function createCollection(
  name: string,
  companyId: string | null,
): Promise<ActionResult<{ name: string }>> {
  const r = await callApi((api) => api.POST("/v1/admin/collections", { body: { name, company_id: companyId } }));
  return r.ok
    ? { ok: true, data: { name: r.data.name } }
    : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

export async function jobStatus(jobId: string) {
  const r = await callApi((api) =>
    api.GET("/v1/documents/jobs/{job_id}", {
      params: { path: { job_id: jobId } },
    }),
  );
  return r.ok
    ? ({
        ok: true,
        data: {
          status: r.data.status,
          chunks: r.data.chunks ?? null,
          error: r.data.error ?? null,
        },
      } as const)
    : ({
        ok: false,
        message: displayMessage(r.error),
        status: r.error.status,
      } as const);
}
