"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

import type { ConfirmResult } from "../confirm-action";

// Apps & keys changes. FastAPI decides who may (super admin or an admin key only). A new key's secret is
// returned to the browser exactly once, to be copied; nothing here stores or logs it.

type KeyCreate = components["schemas"]["KeyCreate"];
type Failure = { ok: false; message: string; status: number };
export type NewKey = { ok: true; apiKey: string; keyId: string; warning?: string } | Failure;

export async function createKey(body: KeyCreate): Promise<NewKey> {
  const r = await callApi((api) => api.POST("/v1/admin/keys", { body }));
  return r.ok
    ? { ok: true, apiKey: r.data.api_key, keyId: r.data.key_id }
    : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

export async function revokeKey(keyId: string): Promise<ConfirmResult> {
  const r = await callApi((api) => api.DELETE("/v1/admin/keys/{key_id}", { params: { path: { key_id: keyId } } }));
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

// Rotate = a new key with the same app, scopes, collections and validity length, then the old one revoked.
// ponytail: two calls; if the revoke fails both keys work, and the result says so (revoke it by hand).
export async function rotateKey(keyId: string): Promise<NewKey> {
  const keys = await callApi((api) => api.GET("/v1/admin/keys"));
  if (!keys.ok) return { ok: false, message: displayMessage(keys.error), status: keys.error.status };
  const old = keys.data.find((k) => k.key_id === keyId);
  if (!old || old.revoked_at) return { ok: false, message: "This key is already revoked.", status: 409 };

  const days = old.expires_at
    ? Math.min(730, Math.max(1, Math.round((Date.parse(old.expires_at) - Date.parse(old.created_at)) / 86_400_000)))
    : null;
  const created = await createKey({
    app_id: old.app_id,
    company_id: old.company_id, // the same client company (6C.1)
    scopes: old.scopes as KeyCreate["scopes"],
    allowed_collections: old.allowed_collections,
    valid_days: days,
  });
  if (!created.ok) return created;

  const revoked = await revokeKey(keyId);
  return revoked.ok
    ? created
    : { ...created, warning: `The old key ${keyId} could NOT be revoked (${revoked.message}). Revoke it by hand.` };
}

// Expiry is sent only when it changes: FastAPI counts valid_days from today (null = never expires).
export async function editKey(
  keyId: string,
  allowedCollections: string[],
  expiry: { change: false } | { change: true; validDays: number | null },
): Promise<ConfirmResult> {
  const body = expiry.change
    ? { allowed_collections: allowedCollections, valid_days: expiry.validDays }
    : { allowed_collections: allowedCollections };
  const r = await callApi((api) => api.PATCH("/v1/admin/keys/{key_id}", { params: { path: { key_id: keyId } }, body }));
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

export async function saveProfile(
  appId: string,
  profile: components["schemas"]["AppProfileIn"],
): Promise<ConfirmResult> {
  const r = await callApi((api) =>
    api.PUT("/v1/admin/apps/{app_id}", { params: { path: { app_id: appId } }, body: profile }),
  );
  return r.ok ? { ok: true } : { ok: false, message: displayMessage(r.error), status: r.error.status };
}

// Disconnect an app: every active key revoked, profile removed; with eraseChats, all its users' chats deleted.
export async function disconnectApp(appId: string, eraseChats: boolean) {
  const r = await callApi((api) =>
    api.POST("/v1/admin/apps/{app_id}/disconnect", {
      params: { path: { app_id: appId } },
      body: { erase_chats: eraseChats },
    }),
  );
  return r.ok
    ? ({ ok: true, data: r.data } as const)
    : ({ ok: false, message: displayMessage(r.error), status: r.error.status } as const);
}

// Remove a disconnected app with no chats left, for good: its revoked key rows and profile go, so it leaves the list.
export async function removeApp(appId: string) {
  const r = await callApi((api) => api.DELETE("/v1/admin/apps/{app_id}", { params: { path: { app_id: appId } } }));
  return r.ok
    ? ({ ok: true, data: r.data } as const)
    : ({ ok: false, message: displayMessage(r.error), status: r.error.status } as const);
}
