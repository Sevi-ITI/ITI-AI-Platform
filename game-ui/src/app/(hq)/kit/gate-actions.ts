"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";

import type { ConfirmResult } from "./confirm-action";

// 8.6e-3: the security password gate (super admin only). The password goes straight to FastAPI from the server and is
// never kept or logged here. Wrong = 403 wrong_security_password, 5 wrong = 423 gate_locked (never 401: no logout).

const result = (r: Awaited<ReturnType<typeof callApi>>): ConfirmResult =>
  r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };

export async function unlockGate(password: string): Promise<ConfirmResult> {
  return result(await callApi((api) => api.POST("/v1/admin/tools/gate/unlock", { body: { password } })));
}

export async function lockGate(): Promise<ConfirmResult> {
  return result(await callApi((api) => api.POST("/v1/admin/tools/gate/lock")));
}
