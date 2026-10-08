import "server-only";

import { cache } from "react";

import { callApi } from "@/lib/api/client";

// The logged-in person (GET /v1/console/me), asked once per request: the layout and any page that needs
// the role share the same answer. Hiding things by role is only cosmetic; FastAPI enforces every permission.
export const currentAccount = cache(() => callApi((api) => api.GET("/v1/console/me")));
