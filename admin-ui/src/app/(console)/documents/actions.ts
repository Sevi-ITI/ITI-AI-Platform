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

// Delete an empty collection (FastAPI refuses one with documents, or one listed in the server settings) and take
// it off every key. Super admin only.
export async function deleteCollection(name: string): Promise<ConfirmResult> {
  const r = await callApi((api) => api.DELETE("/v1/admin/collections/{name}", { params: { path: { name } } }));
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

// Give a collection to another company, or make it Global (companyId null). FastAPI refuses while an active key of
// a different company uses it.
export async function moveCollection(name: string, companyId: string | null): Promise<ConfirmResult> {
  const r = await callApi((api) =>
    api.PATCH("/v1/admin/collections/{name}", { params: { path: { name } }, body: { company_id: companyId } }),
  );
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}
