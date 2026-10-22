"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

import type { ConfirmResult } from "../confirm-action";

// ITI's client companies. Super admin only (FastAPI refuses supervisors).

const result = (r: Awaited<ReturnType<typeof callApi>>): ConfirmResult =>
  r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };

export async function addCompany(company: { company_id: string; name: string; notes: string | null; app_ids: string[] }) {
  return result(await callApi((api) => api.POST("/v1/admin/companies", { body: company })));
}

export async function updateCompany(companyId: string, change: { name: string; notes: string | null }) {
  return result(
    await callApi((api) =>
      api.PATCH("/v1/admin/companies/{company_id}", { params: { path: { company_id: companyId } }, body: change }),
    ),
  );
}

// The whole list of apps linked to the company. FastAPI refuses to unlink an app that still has an active key here.
export async function linkApps(companyId: string, appIds: string[]) {
  return result(
    await callApi((api) =>
      api.PUT("/v1/admin/companies/{company_id}/apps", {
        params: { path: { company_id: companyId } },
        body: { app_ids: appIds },
      }),
    ),
  );
}

// 8.6M: where a company's database is for one system (direct or relay). Only .env variable NAMES are sent, never
// a secret. Changes need the security password (FastAPI refuses them otherwise).
type DatabaseIn = components["schemas"]["CompanyDatabaseIn"];
type ConnectionTest = components["schemas"]["ConnectionTest"];
const where = (companyId: string, system: string) => ({ params: { path: { company_id: companyId, system } } });

export async function saveCompanyDatabase(companyId: string, system: string, body: DatabaseIn): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.PUT("/v1/admin/tools/company-databases/{company_id}/{system}", { ...where(companyId, system), body })),
  );
}

export async function deleteCompanyDatabase(companyId: string, system: string): Promise<ConfirmResult> {
  return result(await callApi((api) => api.DELETE("/v1/admin/tools/company-databases/{company_id}/{system}", where(companyId, system))));
}

export async function testCompanyDatabase(
  companyId: string,
  system: string,
): Promise<{ ok: true; test: ConnectionTest } | { ok: false; message: string; status: number }> {
  const r = await callApi((api) => api.POST("/v1/admin/tools/company-databases/{company_id}/{system}/test", where(companyId, system)));
  return r.ok ? { ok: true, test: r.data } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

// Only a company with no collections and no working keys can be deleted (its revoked keys go with it); FastAPI says what's left.
export async function deleteCompany(companyId: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) =>
      api.DELETE("/v1/admin/companies/{company_id}", { params: { path: { company_id: companyId } } }),
    ),
  );
}
