"""CONSOLE_SCOPES: what each console role may do, in the same scope words the API keys use.
"admin:read" exists only here (no key can be given it): it opens the admin GET routes, i.e. reading.
Supervisors get "documents:write" for NEW uploads; replacing is refused separately (check_can_replace).
Testers get only "chat:invoke": every admin route and every upload is refused (403 scope_forbidden)."""

CONSOLE_SCOPES = {
    "super_admin": ["admin", "chat:invoke", "documents:write"],
    "supervisor": ["admin:read", "chat:invoke", "documents:write"],
    "tester": ["chat:invoke"],
}
