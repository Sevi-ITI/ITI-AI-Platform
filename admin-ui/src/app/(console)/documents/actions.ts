"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";

import type { ConfirmResult } from "../confirm-action";

// Remove a file completely (every version, its chunks). Super admin only: FastAPI refuses supervisors, and
// refuses a file that is still being indexed (409 upload_in_progress, shown as FastAPI's message).
export async function deleteDocument(collection: string, filename: string): Promise<ConfirmResult> {
  const r = await callApi((api) => api.DELETE("/v1/admin/documents", { params: { query: { collection, filename } } }));
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}
