"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

import type { ConfirmResult } from "../confirm-action";

// Tools & MCP changes (super admin only; FastAPI refuses everyone else and every part whose kill switch is off).
// Secrets never pass through here: a connection names the backend\.env variable that holds its secret.

type ConnectionIn = components["schemas"]["ConnectionIn"];
type SqlToolIn = components["schemas"]["SqlToolIn"];
export type ConnectionTest = components["schemas"]["ConnectionTest"];
export type SqlToolCheck = components["schemas"]["SqlToolCheck"];

const result = (r: Awaited<ReturnType<typeof callApi>>): ConfirmResult =>
  r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };

export async function setRecordsSource(source: "builtin" | "mcp"): Promise<ConfirmResult> {
  return result(await callApi((api) => api.PUT("/v1/admin/tools/settings", { body: { records_source: source } })));
}

export async function saveConnection(name: string, body: ConnectionIn): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.PUT("/v1/admin/tools/connections/{name}", { params: { path: { name } }, body })),
  );
}

export async function deleteConnection(name: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.DELETE("/v1/admin/tools/connections/{name}", { params: { path: { name } } })),
  );
}

export async function testConnection(name: string): Promise<{ ok: true; test: ConnectionTest } | { ok: false; message: string; status: number }> {
  const r = await callApi((api) =>
    api.POST("/v1/admin/tools/connections/{name}/test", { params: { path: { name } } }),
  );
  return r.ok ? { ok: true, test: r.data } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

export async function setToolEnabled(name: string, enabled: boolean): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.PUT("/v1/admin/tools/tools/{name}", { params: { path: { name } }, body: { enabled, reset_description: false, approve: false } })),
  );
}

export async function setToolDescription(name: string, description: string | null): Promise<ConfirmResult> {
  const body =
    description === null
      ? { reset_description: true, approve: false }
      : { description, reset_description: false, approve: false };
  return result(await callApi((api) => api.PUT("/v1/admin/tools/tools/{name}", { params: { path: { name } }, body })));
}

// A tool from another machine (http MCP server) is offered only after this; a change to its text or arguments on
// the server makes it wait again.
export async function approveTool(name: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) =>
      api.PUT("/v1/admin/tools/tools/{name}", {
        params: { path: { name } },
        body: { approve: true, reset_description: false },
      }),
    ),
  );
}

export async function saveSqlTool(name: string, body: SqlToolIn): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.PUT("/v1/admin/tools/sql-tools/{name}", { params: { path: { name } }, body })),
  );
}

export async function checkSqlTool(name: string, body: SqlToolIn): Promise<{ ok: true; check: SqlToolCheck } | { ok: false; message: string; status: number }> {
  const r = await callApi((api) =>
    api.POST("/v1/admin/tools/sql-tools/{name}/check", { params: { path: { name } }, body }),
  );
  return r.ok ? { ok: true, check: r.data } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

// Try it (switch "try_it"): one question as a test employee ID with the ticked tool scopes, through the real chat's
// tool loop. It reads REAL records; FastAPI logs every use (who, test ID, scopes, tools; never the question or answer).
export type TryOut = components["schemas"]["TryOut"];

export async function tryTools(body: components["schemas"]["TryIn"]): Promise<{ ok: true; result: TryOut } | { ok: false; message: string; status: number }> {
  const r = await callApi((api) => api.POST("/v1/admin/tools/try", { body }));
  return r.ok ? { ok: true, result: r.data } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

export async function deleteSqlTool(name: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) => api.DELETE("/v1/admin/tools/sql-tools/{name}", { params: { path: { name } } })),
  );
}
