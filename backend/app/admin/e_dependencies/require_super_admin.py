"""require_super_admin(): dependency for admin routes that even supervisors may not READ (console accounts).
Only the "admin" scope passes: an admin key or a super admin's session."""

from app.auth.e_dependencies.require_scope import require_scope

require_super_admin = require_scope("admin")
