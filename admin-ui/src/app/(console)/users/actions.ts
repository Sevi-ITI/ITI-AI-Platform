"use server";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";

// Erase one user's chats in one app (RA 10173 requests, offboarding). FastAPI refuses anyone but a super
// admin; the console only hides the button for supervisors.
export async function deleteUserChats(appId: string, userId: string) {
  const r = await callApi((api) =>
    api.DELETE("/v1/admin/conversations", { params: { query: { app_id: appId, user_id: userId } } }),
  );
  return r.ok
    ? ({ ok: true, data: { conversations: r.data.conversations, messages: r.data.messages } } as const)
    : ({ ok: false, message: displayMessage(r.error), status: r.error.status } as const);
}
