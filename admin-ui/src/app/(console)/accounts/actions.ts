"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

import type { ConfirmResult } from "../confirm-action";

// Console accounts (super admin only; FastAPI refuses everyone else). Passwords pass straight through to
// FastAPI, which hashes them; nothing here keeps or logs them.

type Role = components["schemas"]["AccountInfo"]["role"];

const result = (r: Awaited<ReturnType<typeof callApi>>): ConfirmResult =>
  r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };

export async function addAccount(account: {
  username: string;
  display_name: string | null;
  role: Role;
  password: string;
}): Promise<ConfirmResult> {
  return result(await callApi((api) => api.POST("/v1/admin/accounts", { body: account })));
}

export async function updateAccount(
  username: string,
  change: { display_name?: string | null; role?: Role; active?: boolean },
): Promise<ConfirmResult> {
  return result(
    await callApi((api) =>
      api.PATCH("/v1/admin/accounts/{username}", { params: { path: { username } }, body: change }),
    ),
  );
}

export async function resetPassword(username: string, password: string): Promise<ConfirmResult> {
  return result(
    await callApi((api) =>
      api.POST("/v1/admin/accounts/{username}/password", { params: { path: { username } }, body: { password } }),
    ),
  );
}
