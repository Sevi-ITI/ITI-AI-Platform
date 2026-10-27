import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/lib/console-app";

// First gate only: no session cookie → the login page. Whether the pass is still valid is checked by
// FastAPI on every call (a 401 → /session-ended), so this never decides who may do what. /api/documents is left out
// (as in admin-ui): the proxy buffers only 10 MB of a body, and uploads stream through; that route checks itself.
export function proxy(request: NextRequest) {
  if (!request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/((?!login|session-ended|api/documents|_next/static|_next/image|favicon.ico).*)"],
};
