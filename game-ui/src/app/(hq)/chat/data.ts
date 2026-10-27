import "server-only";

import { cache } from "react";

import { callApi } from "@/lib/api/client";

// The logged-in person's own conversations (app iti-console, user = their username), newest first.
// Asked once per request: the chat layout (list) and a conversation page (its collection) share it.
export const myConversations = cache(() =>
  callApi((api) => api.GET("/v1/conversations", { params: { query: { limit: 50 } } })),
);

// The collections this person may ask (a tester: only theirs), with document counts and newest files, for the
// picker, the suggestion chips and the upload dialog (new chat and conversation pages).
export const chatCollections = cache(() => callApi((api) => api.GET("/v1/console/collections")));
