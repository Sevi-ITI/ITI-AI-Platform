import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/lib/session/cookie";

// First gate only: no session cookie → the login page. Whether the pass is still valid is checked by
// FastAPI on every call (a 401 → /session-ended), so this never decides who may do what.
export function proxy(request: NextRequest) {
  if (!request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/((?!login|session-ended|_next/static|_next/image|favicon.ico).*)"],
};
