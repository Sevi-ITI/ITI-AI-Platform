"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";

import type { ConfirmResult } from "../confirm-action";

// ITI's client companies. Super admin only (FastAPI refuses supervisors).

const result = (r: Awaited<ReturnType<typeof callApi>>): ConfirmResult =>
  r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };

export async function addCompany(company: { company_id: string; name: string; notes: string | null }) {
  return result(await callApi((api) => api.POST("/v1/admin/companies", { body: company })));
}

export async function updateCompany(companyId: string, change: { name: string; notes: string | null }) {
  return result(
    await callApi((api) =>
      api.PATCH("/v1/admin/companies/{company_id}", { params: { path: { company_id: companyId } }, body: change }),
    ),
  );
}

// Only a company that owns nothing (no collections, no keys of any state) can be deleted; FastAPI says what's left.
export async function deleteCompany(companyId: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) =>
      api.DELETE("/v1/admin/companies/{company_id}", { params: { path: { company_id: companyId } } }),
    ),
  );
}
