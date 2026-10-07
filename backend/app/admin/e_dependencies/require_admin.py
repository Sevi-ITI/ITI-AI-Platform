"""require_admin(): dependency: a valid key with the "admin" scope."""

from app.auth.e_dependencies.require_scope import require_scope

require_admin = require_scope("admin")
